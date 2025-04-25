import NewGuru from "@/components/NewGuru";

const NewGuruContent = ({
  guruData,
  isProcessing,
  setHasDataSources,
  hasDataSources
}) => {
  return (
    <NewGuru
      guruData={guruData}
      hasDataSources={hasDataSources}
      isProcessing={isProcessing}
      setHasDataSources={setHasDataSources}
    />
  );
};

export default NewGuruContent;
