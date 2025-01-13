const ExampleQuestions = ({ questions, onQuestionClick }) => {
  if (!Array.isArray(questions) || questions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {questions.map((question, index) => (
        <button
          key={index}
          className="px-4 py-2 bg-white rounded-[12px] border border-neutral-200 text-sm hover:border-neutral-300 transition-colors text-left"
          onClick={(e) => onQuestionClick(question, e)}
          aria-label={`Example question: ${question}`}>
          {question}
        </button>
      ))}
    </div>
  );
};

export default ExampleQuestions;
