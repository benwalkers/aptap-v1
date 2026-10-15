"""ONE-TIME ONLINE PROVISIONING. Never invoked by production inference."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Download MiniLM for offline use")
    parser.add_argument("--destination", default="models/minilm")
    args = parser.parse_args()
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    destination = Path(args.destination)
    destination.mkdir(parents=True, exist_ok=True)
    model.save(str(destination))
    print(f"MiniLM saved in {destination.resolve()}")

if __name__ == "__main__":
    main()
