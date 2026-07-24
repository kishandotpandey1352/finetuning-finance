import logging
import os
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import boto3
import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger("finance-inference-loader")


DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_ADAPTER_S3_URI = "s3://finance-llm-local-artifacts-671607590681-us-east-1/models/qwen2.5-3b-finance/runB-r16-lr2e4/adapter/"



def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    if value is None:
        return None
    value = value.strip()
    return value if value else default


def parse_s3_uri(s3_uri: str):
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Expected S3 URI, got: {s3_uri}")

    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")

    if not bucket:
        raise ValueError(f"Invalid S3 URI, missing bucket: {s3_uri}")

    return bucket, prefix


def download_s3_prefix(s3_uri: str, local_dir: Path) -> None:
    bucket, prefix = parse_s3_uri(s3_uri)

    if local_dir.exists():
        shutil.rmtree(local_dir)

    local_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading adapter from %s to %s", s3_uri, local_dir)

    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    found_any = False

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if key.endswith("/"):
                continue

            found_any = True
            relative_path = key[len(prefix):].lstrip("/")
            destination = local_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)

            logger.info("Downloading s3://%s/%s -> %s", bucket, key, destination)
            s3.download_file(bucket, key, str(destination))

    if not found_any:
        raise FileNotFoundError(f"No objects found under {s3_uri}")


def validate_adapter_dir(adapter_dir: Path) -> None:
    required_files = [
        "adapter_config.json",
        "adapter_model.safetensors",
        "tokenizer_config.json",
        "tokenizer.json",
        "README.md",
    ]

    missing = []

    for file_name in required_files:
        file_path = adapter_dir / file_name
        if not file_path.exists():
            missing.append(file_name)

    if missing:
        raise FileNotFoundError(
            f"Adapter directory is missing required files: {missing}. "
            f"Adapter dir: {adapter_dir}"
        )

    logger.info("Adapter directory validated: %s", adapter_dir)


class FinanceLLM:
    def __init__(
        self,
        base_model_name: str = DEFAULT_BASE_MODEL,
        adapter_s3_uri: str = DEFAULT_ADAPTER_S3_URI,
        local_adapter_dir: str = "/tmp/qwen2.5-3b-finance-adapter",
        load_in_4bit: bool = True,
        device_map: str = "auto",
        hf_token: Optional[str] = None,
    ):
        self.base_model_name = base_model_name
        self.adapter_s3_uri = adapter_s3_uri
        self.local_adapter_dir = Path(local_adapter_dir)
        self.load_in_4bit = load_in_4bit
        self.device_map = device_map
        self.hf_token = hf_token

        self.tokenizer = None
        self.model = None

    def prepare_adapter(self) -> None:
        adapter_local_override = get_env("ADAPTER_LOCAL_DIR")

        if adapter_local_override:
            logger.info("Using local adapter directory override: %s", adapter_local_override)
            self.local_adapter_dir = Path(adapter_local_override)
        else:
            download_s3_prefix(self.adapter_s3_uri, self.local_adapter_dir)

        validate_adapter_dir(self.local_adapter_dir)

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            logger.info("Model already loaded.")
            return

        logger.info("Preparing adapter...")
        self.prepare_adapter()

        logger.info("Loading tokenizer from adapter directory: %s", self.local_adapter_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.local_adapter_dir),
            token=self.hf_token,
            trust_remote_code=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        use_cuda = torch.cuda.is_available()
        logger.info("CUDA available: %s", use_cuda)

        quantization_config = None

        if self.load_in_4bit and use_cuda:
            logger.info("Using 4-bit quantized base model loading.")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif self.load_in_4bit and not use_cuda:
            logger.warning(
                "LOAD_IN_4BIT=true but CUDA is not available. "
                "Falling back to non-quantized CPU loading. This may be slow or memory-heavy."
            )

        logger.info("Loading base model: %s", self.base_model_name)

        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            token=self.hf_token,
            trust_remote_code=True,
            device_map=self.device_map if use_cuda else None,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16 if use_cuda else torch.float32,
        )

        logger.info("Attaching PEFT adapter from: %s", self.local_adapter_dir)

        self.model = PeftModel.from_pretrained(
            base_model,
            str(self.local_adapter_dir),
            is_trainable=False,
        )

        self.model.eval()

        logger.info("Finance LLM loaded successfully.")

    def build_prompt(self, user_message: str, system_message: Optional[str] = None) -> str:
        if system_message is None:
            system_message = (
                "You are a careful financial AI assistant. "
                "Provide accurate, concise, risk-aware answers. "
                "Do not provide personalized financial advice."
            )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.chat_template:
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        return (
            f"System: {system_message}\n\n"
            f"User: {user_message}\n\n"
            f"Assistant:"
        )

    def generate(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        max_new_tokens: int = 256,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> str:
        if self.model is None or self.tokenizer is None:
            self.load()

        prompt = self.build_prompt(user_message, system_message)

        inputs = self.tokenizer(prompt, return_tensors="pt")

        if torch.cuda.is_available():
            inputs = {key: value.to(self.model.device) for key, value in inputs.items()}

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

        return response.strip()

    def summarize(self, text: str) -> str:
        prompt = (
            "Summarize the following financial text. "
            "Focus on key business drivers, risks, and important financial details.\n\n"
            f"{text}"
        )
        return self.generate(prompt)

    def answer_question(self, question: str, context: Optional[str] = None) -> str:
        if context:
            prompt = (
                "Answer the financial question using the provided context. "
                "Be concise and mention uncertainty where relevant.\n\n"
                f"Context:\n{context}\n\n"
                f"Question:\n{question}"
            )
        else:
            prompt = (
                "Answer the following financial question. "
                "Be concise and risk-aware.\n\n"
                f"Question:\n{question}"
            )

        return self.generate(prompt)

    def analyze_risk(self, text: str) -> str:
        prompt = (
            "Analyze the financial risks in the following text. "
            "Group the answer into market risk, credit risk, liquidity risk, "
            "operational risk, and business risk where applicable.\n\n"
            f"{text}"
        )
        return self.generate(prompt)


_model_instance: Optional[FinanceLLM] = None


def get_finance_llm() -> FinanceLLM:
    global _model_instance

    if _model_instance is None:
        base_model_name = get_env("BASE_MODEL_NAME", DEFAULT_BASE_MODEL)
        adapter_s3_uri = get_env("ADAPTER_S3_URI", DEFAULT_ADAPTER_S3_URI)
        local_adapter_dir = get_env("LOCAL_ADAPTER_DIR", "/tmp/qwen2.5-3b-finance-adapter")
        load_in_4bit = get_env("LOAD_IN_4BIT", "true").lower() == "true"
        device_map = get_env("DEVICE_MAP", "auto")
        hf_token = get_env("HF_TOKEN")

        _model_instance = FinanceLLM(
            base_model_name=base_model_name,
            adapter_s3_uri=adapter_s3_uri,
            local_adapter_dir=local_adapter_dir,
            load_in_4bit=load_in_4bit,
            device_map=device_map,
            hf_token=hf_token,
        )

    return _model_instance