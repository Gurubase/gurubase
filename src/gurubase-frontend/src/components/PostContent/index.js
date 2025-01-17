import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import ArticleSources from "@/components/ArticleSources/index";
import CodeBlock from "@/components/PostContent/CodeBlock";
import FeedbackSection from "@/components/PostContent/FeedbackSection";
import ShareOptions from "@/components/PostContent/ShareOptions";
import { useAppSelector } from "@/redux/hooks";

import EndOfContent from "../EndOfContent";
import SimilarQuestions from "../SimilarQuestions";
import TrustScore from "../TrustScore/trust-score";

// Style configurations for code blocks
const getCodeStyle = (length) => ({
  display: length > 50 ? "contents" : "inline",
  textDecoration: "none",
  wordWrap: "break-word",
  overflowWrap: "break-word",
  whiteSpace: "pre-wrap",
  overflow: length > 50 ? "scroll" : "hidden",
  wordBreak: "break-all"
});

// Memoized custom components for ReactMarkdown
const CustomLink = React.memo(({ node, ...props }) => {
  const hasStrong = node.children.some((child) => child.tagName === "strong");
  const href = props.href;
  const isLocalhost =
    href && (href.includes("localhost") || href.includes("127.0.0.1"));

  if (isLocalhost) {
    return <span {...props} />;
  }

  if (hasStrong) {
    return (
      <a rel="noopener noreferrer" target="_blank" {...props}>
        {node.children.map((child, index) => {
          if (child.tagName === "strong") {
            return (
              <span key={index} className={child.properties.className}>
                {child.children[0].value}
              </span>
            );
          }

          return child;
        })}
      </a>
    );
  }

  return <a rel="noopener noreferrer" target="_blank" {...props} />;
});

const CustomParagraph = React.memo(({ node, children, ...props }) => {
  const hasCode = node.children.some((child) => child.tagName === "code");

  if (!hasCode) {
    return <p {...props}>{children}</p>;
  }

  return (
    <div {...props}>
      {node.children.map((child, index) => {
        if (child.tagName === "code") {
          const codeText = child.children[0].value;

          return (
            <pre key={index} style={getCodeStyle(codeText.length)}>
              <code {...props}>{codeText}</code>
            </pre>
          );
        }

        if (child.tagName === "strong") {
          return (
            <strong key={index} className="text-base">
              {child.children.map((grandChild, grandIndex) => {
                if (grandChild.tagName === "code") {
                  const codeText = grandChild.children[0].value;

                  return (
                    <pre key={grandIndex} style={getCodeStyle(codeText.length)}>
                      <code {...props}>{codeText}</code>
                    </pre>
                  );
                }

                return grandChild.value;
              })}
            </strong>
          );
        }

        if (child.tagName === "a") {
          return (
            <a
              key={index + child.properties.href}
              className="text-[1rem]"
              href={child.properties.href}
              rel="noopener noreferrer"
              target="_blank">
              {child.children[0].value}
            </a>
          );
        }

        return (
          <p key={index} className="inline">
            {child.value}
          </p>
        );
      })}
    </div>
  );
});

const CustomCode = React.memo(
  ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || "");
    const codeText = String(children);

    if (!inline && match) {
      return (
        <CodeBlock
          language={match[1]}
          value={codeText.replace(/\n$/, "")}
          {...props}
          className="no-underline"
        />
      );
    }

    if (!inline && !match && codeText.includes("\n")) {
      return (
        <CodeBlock
          language="plaintext"
          value={codeText.replace(/\n$/, "")}
          {...props}
          className="no-underline"
        />
      );
    }

    if (!inline) {
      return (
        <pre style={getCodeStyle(codeText.length)}>
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      );
    }

    return (
      <code className={`${className} no-underline text-[0.9rem]`} {...props}>
        {children}
      </code>
    );
  }
);

const CustomSpan = React.memo(({ ...props }) => (
  <span {...props} className="no-underline" />
));

// Memoized markdown components configuration
const markdownComponents = {
  a: CustomLink,
  p: CustomParagraph,
  code: CustomCode,
  span: CustomSpan
};

const PostContent = ({
  question,
  content,
  isHelpful,
  slug,
  description,
  guruType,
  references,
  similarQuestions,
  trustScore
}) => {
  const streamingStatus = useAppSelector(
    (state) => state.mainForm.streamingStatus
  );
  const bingeId = useAppSelector((state) => state.mainForm.bingeId);

  // Memoize the ReactMarkdown component to prevent unnecessary re-renders
  const memoizedMarkdown = React.useMemo(
    () => (
      <ReactMarkdown
        components={markdownComponents}
        remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    ),
    [content]
  );

  return (
    <section className="flex flex-col mx-6 pb-20 xs:mx-0 xs:px-4">
      <article className="flex flex-col justify-center p-6 guru-md:p-4 w-full rounded-xl border border-solid bg-neutral-50 border-neutral-200 sm:max-w-full">
        <div className="anteon-prose prose prose-slate prose-base md:prose-sm lg:prose-md prose-pre:p-0 prose-pre:m-0 prose-a:text-blue-600 prose-img:rounded-lg text-zinc-900 sm:max-w-full">
          {memoizedMarkdown}
        </div>
        {!streamingStatus && (
          <EndOfContent>
            <ArticleSources references={references} />
            <TrustScore bingeId={bingeId} score={trustScore} />
          </EndOfContent>
        )}
      </article>
      {!streamingStatus && (
        <div className="flex gap-3 sm:justify-between ml-1 sm:ml-0 justify-start mt-6 w-full flex-wrap sm:max-w-full">
          <FeedbackSection
            content={content}
            description={description}
            guruType={guruType}
            isHelpful={isHelpful}
            question={question}
            slug={slug}
          />
          <ShareOptions description={description} title={question} />
        </div>
      )}
      {!streamingStatus && !bingeId && (
        <SimilarQuestions isMobile={true} similarQuestions={similarQuestions} />
      )}
    </section>
  );
};

export default React.memo(PostContent);
