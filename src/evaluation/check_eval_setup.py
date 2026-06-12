import evaluate
from bert_score import score
from sklearn.metrics import f1_score


def main():
    print("Evaluation setup check")

    rouge = evaluate.load("rouge")

    predictions = [
        "Revenue increased because of stronger cloud demand."
    ]

    references = [
        "Revenue grew due to strong demand for cloud services."
    ]

    rouge_result = rouge.compute(
        predictions=predictions,
        references=references,
    )

    print("ROUGE result:")
    print(rouge_result)

    P, R, F1 = score(
        predictions,
        references,
        lang="en",
        verbose=False,
    )

    print("BERTScore result:")
    print({
        "precision": float(P.mean()),
        "recall": float(R.mean()),
        "f1": float(F1.mean()),
    })

    labels_true = [1, 0, 1, 1]
    labels_pred = [1, 0, 0, 1]

    print("F1 classification score:")
    print(f1_score(labels_true, labels_pred))

    print("Evaluation environment check passed")


if __name__ == "__main__":
    main()