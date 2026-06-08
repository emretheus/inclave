import { describe, expect, it } from "vitest";
import { cleanUserText, cn, formatBytes, formatDuration } from "./utils";

describe("utils", () => {
  it("formatBytes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
    expect(formatBytes(3 * 1024 * 1024 * 1024)).toBe("3.0 GB");
  });

  it("formatDuration", () => {
    expect(formatDuration(500)).toBe("500ms");
    expect(formatDuration(1500)).toBe("1.5s");
  });

  it("cn merges and dedupes tailwind classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
    expect(cn("text-sm", false, "font-bold")).toBe("text-sm font-bold");
  });

  describe("cleanUserText", () => {
    it("passes plain text through untouched", () => {
      expect(cleanUserText("what is the total?")).toEqual({
        text: "what is the total?",
        fileNames: [],
      });
    });

    it("strips a FILE block and surfaces the question + file name", () => {
      const raw =
        "<<<FILE id=abc123 name=q1_review.pdf kind=pdf>>>\nlots of pdf text here\n<<<END FILE>>>\n\n---\n\nsummarize the key points";
      const { text, fileNames } = cleanUserText(raw);
      expect(text).toBe("summarize the key points");
      expect(fileNames).toEqual(["q1_review.pdf"]);
    });

    it("handles multiple files", () => {
      const raw =
        "<<<FILE id=a name=a.csv kind=csv>>>x<<<END FILE>>>\n\n<<<FILE id=b name=b.pdf kind=pdf>>>y<<<END FILE>>>\n\n---\n\ncompare them";
      const { text, fileNames } = cleanUserText(raw);
      expect(text).toBe("compare them");
      expect(fileNames).toEqual(["a.csv", "b.pdf"]);
    });
  });
});
