from __future__ import annotations
import argparse
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer


def main():
    parser = argparse.ArgumentParser(description="Enclave CodeRunner CLI")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--prompt", help="Generation prompt (interactive if omitted)")
    parser.add_argument("--index", action="store_true", help="Re-index knowledge base and exit")
    args = parser.parse_args()

    if args.index:
        indexer = KnowledgeIndexer()
        indexer.index_knowledge_dir(force_reindex=True)
        print(f"Done. {indexer.get_stats()}")
        return

    pipeline = CodePipeline()

    if args.prompt:
        # Single-shot mode
        result = pipeline.generate(args.csv, args.prompt)
        print(result.code)
    else:
        # Interactive mode
        print(f"CSV loaded: {args.csv}")
        print("Type your prompts (Ctrl+C to exit):\n")
        while True:
            try:
                prompt = input(">>> ")
                if not prompt.strip():
                    continue
                result = pipeline.generate(args.csv, prompt)
                print(f"\n{result.code}\n")
            except KeyboardInterrupt:
                print("\nBye.")
                break


if __name__ == "__main__":
    main()