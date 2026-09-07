import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders LLM-generated chat/reply text as markdown instead of raw text -
 * without this, a model reply like "**Sitapur** has:\n- low competition\n- ..."
 * showed up on screen as literal asterisks and dashes instead of formatting.
 *
 * Deliberately restricted to inline-safe elements (no raw HTML, no images) -
 * this only ever renders model output, so keep it to plain prose formatting.
 */
export default function Markdown({ children, className = "" }) {
  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" className="underline decoration-2 underline-offset-2" />,
          ul: ({ node, ...props }) => <ul {...props} className="list-disc pl-5 space-y-1 my-1.5" />,
          ol: ({ node, ...props }) => <ol {...props} className="list-decimal pl-5 space-y-1 my-1.5" />,
          p: ({ node, ...props }) => <p {...props} className="my-1 first:mt-0 last:mb-0" />,
          strong: ({ node, ...props }) => <strong {...props} className="font-bold" />,
          code: ({ node, ...props }) => <code {...props} className="rounded bg-black/5 px-1 py-0.5 text-[0.9em]" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
