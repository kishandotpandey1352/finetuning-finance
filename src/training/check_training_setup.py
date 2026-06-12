import os
import torch
from transformers import AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig


def main():
    model_name = os.getenv("LOCAL_TEST_MODEL", "Qwen/Qwen2.5-3B-Instruct")

    print("Training setup check")
    print(f"Model for local test: {model_name}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("No GPU detected inside Docker. CPU-only checks will run.")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    print("Tokenizer loaded successfully")
    print(f"Vocab size: {len(tokenizer)}")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    print("BitsAndBytesConfig created")
    print(bnb_config)

    print("LoRA config created")
    print(lora_config)

    print("Training environment check passed")


if __name__ == "__main__":
    main()