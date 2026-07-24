import os

from src.inference.model_loader_eks import get_finance_llm


def main() -> None:
    print("Starting finance model loader test...")

    model = get_finance_llm()

    test_prompt = (
        "A company reports revenue growth of 12%, declining gross margin, "
        "and higher interest expense. What are the key financial risks?"
    )

    response = model.generate(
        test_prompt,
        max_new_tokens=int(os.getenv("MAX_NEW_TOKENS", "200")),
        temperature=float(os.getenv("TEMPERATURE", "0.2")),
    )

    print("\nPrompt:")
    print(test_prompt)

    print("\nModel response:")
    print(response)


if __name__ == "__main__":
    main()