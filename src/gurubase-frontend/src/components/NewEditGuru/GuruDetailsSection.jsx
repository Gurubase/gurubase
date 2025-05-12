import React, { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { HeaderTooltip } from "@/components/ui/header-tooltip";
import { SolarGalleryAddBold } from "@/components/Icons";
import { Upload } from "lucide-react";
import CustomPrompt from "./CustomPrompt";
import { getPromptTemplates } from "@/app/actions";

export function GuruDetailsSection({
  form,
  isEditMode,
  isProcessing,
  isSubmitting,
  isSourcesProcessing,
  iconUrl,
  selectedFile,
  setSelectedFile,
  setIconUrl,
  setDirtyChanges,
  allowCustomPrompt,
  guruData
}) {
  const [templates, setTemplates] = useState([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);

  // Add handler for prompt changes
  const handlePromptChange = useCallback(
    ({ content, templateId, isModified }) => {
      if (isModified) {
        setDirtyChanges((prev) => ({
          ...prev,
          promptUpdated: true,
          promptContent: content,
          promptTemplateId: templateId
        }));
      } else {
        setDirtyChanges((prev) => ({
          ...prev,
          promptUpdated: false,
          promptContent: content,
          promptTemplateId: templateId
        }));
      }
    },
    [setDirtyChanges]
  );

  useEffect(() => {
    const fetchTemplates = async () => {
      if (!guruData?.slug) {
        setIsLoadingTemplates(false);
        return;
      }

      setIsLoadingTemplates(true);
      try {
        const data = await getPromptTemplates(guruData.slug);

        if (data && !data.error && data.prompts) {
          setTemplates(data.prompts);
        } else {
        }
      } catch (error) {
      } finally {
        setIsLoadingTemplates(false);
      }
    };

    fetchTemplates();
  }, [guruData?.slug]);

  return (
    <div>
      <div className="max-w-md">
        <FormField
          control={form.control}
          name="guruName"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center space-x-2">
                <FormLabel>
                  Guru Name <span className="text-red-500">*</span>
                </FormLabel>
                <HeaderTooltip
                  text={
                    isEditMode
                      ? "Guru name cannot be changed"
                      : "Enter the name of your AI guru"
                  }
                />
              </div>
              <FormControl>
                <Input
                  placeholder="Enter a guru name"
                  {...field}
                  className={
                    isEditMode || isProcessing || isSubmitting
                      ? "bg-gray-100 cursor-not-allowed"
                      : ""
                  }
                  disabled={isEditMode || isProcessing || isSubmitting}
                  onBlur={() => form.trigger("guruName")}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="guruLogo"
          render={({ field: { value, onChange, ...rest } }) => (
            <FormItem>
              <div className="flex items-center space-x-2">
                <FormLabel>
                  Guru Logo <span className="text-red-500">*</span>
                </FormLabel>
                <HeaderTooltip text={"Guru logo"} />
              </div>
              <FormControl>
                <div className="flex items-center space-x-4">
                  <div className="w-16 h-16 bg-gray-900 rounded-lg border-[0.5px] border-gray-85 flex items-center justify-center overflow-hidden">
                    {iconUrl ? (
                      <Image
                        alt="Guru logo"
                        className="w-full h-full object-cover"
                        height={64}
                        src={iconUrl}
                        width={64}
                      />
                    ) : selectedFile ? (
                      <Image
                        alt="Selected logo"
                        className="w-full h-full object-cover"
                        height={64}
                        src={URL.createObjectURL(selectedFile)}
                        width={64}
                      />
                    ) : (
                      <div>
                        <SolarGalleryAddBold
                          className="text-gray-500"
                          height={26.66}
                          width={26.66}
                        />
                      </div>
                    )}
                  </div>
                  <div>
                    <Input
                      accept="image/png, image/jpeg"
                      className="hidden"
                      id="logo-upload"
                      type="file"
                      onChange={(e) => {
                        const file = e.target.files?.[0];

                        if (file) {
                          setSelectedFile(file);
                          setIconUrl(null);
                          onChange(file);
                          // Mark form as dirty when logo changes
                          setDirtyChanges((prev) => ({
                            ...prev,
                            guruUpdated: true
                          }));
                        }
                      }}
                      {...rest}
                      value="" // Always keep the value empty for file inputs
                    />
                    <Button
                      className="text-gray-600 hover:text-gray-700 mb-2"
                      disabled={isProcessing || isSubmitting}
                      type="button"
                      variant="outline"
                      onClick={() =>
                        document.getElementById("logo-upload").click()
                      }>
                      <Upload className="mr-2 h-4 w-4" />{" "}
                      {isEditMode ? "Change Logo" : "Upload Logo"}
                    </Button>
                    <FormDescription>
                      We support PNG, JPEG under 1MB.
                    </FormDescription>
                  </div>
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="guruContext"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center space-x-2">
                <FormLabel>
                  Topics <span className="text-red-500">*</span>
                </FormLabel>
                <HeaderTooltip
                  text={
                    'Add comma-separated topics related to this Guru, e.g., "programming, microservices, containers". This helps the AI understand the Guru\'s expertise and context.'
                  }
                />
              </div>
              <FormControl>
                <Input
                  placeholder="Enter topics, separated by commas"
                  {...field}
                  className="w-full"
                  disabled={isSourcesProcessing || isProcessing || isSubmitting}
                  onBlur={() => form.trigger("guruContext")}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>
      {allowCustomPrompt && (
        <CustomPrompt
          guruType={guruData.slug}
          templates={templates}
          isLoading={isLoadingTemplates}
          onPromptChange={handlePromptChange}
        />
      )}
    </div>
  );
}
