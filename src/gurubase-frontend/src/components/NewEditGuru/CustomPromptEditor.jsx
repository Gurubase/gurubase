"use client";

import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from "@/components/ui/form";
import { HeaderTooltip } from "@/components/ui/header-tooltip";
import { useForm } from "react-hook-form";
import { ChevronDown } from "lucide-react";

export default function CustomPromptEditor({
  onPromptChange,
  templates,
  isSourcesProcessing,
  isProcessing,
  isSubmitting
}) {
  const [selectedPreset, setSelectedPreset] = useState("current_prompt");
  const [originalContent, setOriginalContent] = useState("");
  const form = useForm({
    defaultValues: {
      promptContent: ""
    }
  });

  // Update content when templates change
  useEffect(() => {
    const currentPrompt = templates?.find((t) => t.id === "current_prompt");
    if (currentPrompt) {
      form.setValue("promptContent", currentPrompt.content);
      setOriginalContent(currentPrompt.content);
    }
    setSelectedPreset("current_prompt");
  }, [templates, form]);

  const handlePresetChange = (value) => {
    const template = templates.find((t) => t.id === value);
    if (template) {
      setSelectedPreset(value);
      form.setValue("promptContent", template.content);
      // Only mark as modified if the content differs from original prompt
      const isModified = template.content !== originalContent;
      onPromptChange?.({
        content: template.content,
        templateId: value,
        isModified,
        isCustomPrompt: value !== "current_prompt"
      });
    }
  };

  const handleReset = () => {
    // Find the template for the currently selected preset
    const selectedTemplate = templates.find((t) => t.id === selectedPreset);
    if (selectedTemplate) {
      form.setValue("promptContent", selectedTemplate.content);
      // Only mark as modified if the content differs from original prompt
      const isModified = selectedTemplate.content !== originalContent;
      onPromptChange?.({
        content: selectedTemplate.content,
        templateId: selectedPreset,
        isModified,
        isCustomPrompt: selectedPreset !== "current_prompt"
      });
    }
  };

  // Add form watch to track content changes
  useEffect(() => {
    const subscription = form.watch((value, { name, type }) => {
      if (name === "promptContent" && type === "change") {
        onPromptChange?.({
          content: value.promptContent,
          templateId: selectedPreset,
          isModified: value.promptContent !== originalContent,
          isCustomPrompt: selectedPreset !== "current_prompt"
        });
      }
    });
    return () => subscription.unsubscribe();
  }, [form, selectedPreset, originalContent, onPromptChange]);

  return (
    <div>
      <div className="flex items-center space-x-2 mb-6">
        <h3 className="text-sm font-medium">Custom Prompt</h3>
        <HeaderTooltip text="Customize the prompt instructions for your guru" />
      </div>

      <div className="space-y-6">
        <div>
          <div className="flex items-center space-x-2">
            <Select
              disabled={isSourcesProcessing || isProcessing || isSubmitting}
              value={selectedPreset}
              onValueChange={handlePresetChange}>
              <SelectTrigger className="w-full md:w-[300px] rounded-[12px] focus:ring-0 focus:ring-offset-0">
                <SelectValue placeholder="Select a template" />
                <ChevronDown className="h-4 w-4 ml-2 text-gray-500" />
              </SelectTrigger>
              <SelectContent>
                {templates?.map((template) => (
                  <SelectItem key={template.id} value={template.id}>
                    {template.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              disabled={isSourcesProcessing || isProcessing || isSubmitting}
              variant="outline"
              onClick={(e) => {
                e.preventDefault();
                handleReset();
              }}>
              Reset
            </Button>
          </div>
        </div>

        <Form {...form}>
          <FormField
            control={form.control}
            name="promptContent"
            disabled={isSourcesProcessing || isProcessing || isSubmitting}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Textarea
                    {...field}
                    className="min-h-[150px] font-mono text-sm resize-y"
                    placeholder="Prompt instructions will appear here"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </Form>
      </div>
    </div>
  );
}
