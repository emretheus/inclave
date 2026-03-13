import argparse
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer


def main():
    parser = argparse.ArgumentParser(description="Enclave CodeRunner CLI")
    parser.add_argument("--csv", required=True, help="Path to primary CSV file")
    parser.add_argument("--csv2", help="Path to secondary CSV file (optional, for merge operations)")
    parser.add_argument("--prompt", help="Generation prompt (interactive if omitted)")
    parser.add_argument("--index", action="store_true", help="Re-index knowledge base and exit")
    args = parser.parse_args()

    if args.index:
        indexer = KnowledgeIndexer()
        indexer.index_knowledge_dir(force_reindex=True)
        print(f"Done. {indexer.get_stats()}")
        return

    pipeline = CodePipeline()

    # Build context note about second CSV if provided
    csv2_note = ""
    if args.csv2:
        csv2_note = f"\nA second CSV file is also available at: {args.csv2}"

    if args.prompt:
        # Single-shot mode
        full_prompt = args.prompt + csv2_note
        result = pipeline.generate(args.csv, full_prompt)
        print(result.code)
    else:
        # Interactive mode
        print(f"Primary CSV: {args.csv}")
        if args.csv2:
            print(f"Secondary CSV: {args.csv2}")
        print("Type your prompts (Ctrl+C to exit):\n")
        while True:
            try:
                prompt = input(">>> ")
                if not prompt.strip():
                    continue
                full_prompt = prompt + csv2_note
                result = pipeline.generate(args.csv, full_prompt)
                print(f"\n{result.code}\n")
            except KeyboardInterrupt:
                print("\nBye.")
                break


if __name__ == "__main__":
    main()