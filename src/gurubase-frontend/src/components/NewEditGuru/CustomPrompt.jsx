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
import { Skeleton } from "@/components/ui/skeleton";

export default function PromptEditor({
  guruType,
  templates,
  isLoading,
  onPromptChange
}) {
  const [selectedPreset, setSelectedPreset] = useState("current_prompt");
  const [originalContent, setOriginalContent] = useState("");
  const form = useForm({
    defaultValues: {
      promptContent: ""
    }
  });

  // Set initial content when templates are loaded
  useEffect(() => {
    if (templates?.length > 0) {
      const currentPrompt = templates.find((t) => t.id === "current_prompt");
      if (currentPrompt) {
        form.setValue("promptContent", currentPrompt.content);
        setOriginalContent(currentPrompt.content);
      }
    }
  }, [templates, form]);

  // Update form content when preset changes
  useEffect(() => {
    if (selectedPreset && templates?.length > 0) {
      const template = templates.find((t) => t.id === selectedPreset);
      if (template) {
        form.setValue("promptContent", template.content);
        if (selectedPreset === "current_prompt") {
          setOriginalContent(template.content);
        }
        // Notify parent of prompt change
        onPromptChange?.({
          content: template.content,
          templateId: selectedPreset,
          isModified:
            selectedPreset !== "current_prompt" ||
            template.content !== originalContent
        });
      }
    }
  }, [selectedPreset, templates, form, originalContent, onPromptChange]);

  const handlePresetChange = (value) => {
    setSelectedPreset(value);
  };

  const handleReset = () => {
    form.setValue("promptContent", originalContent);
    // Notify parent of reset
    onPromptChange?.({
      content: originalContent,
      templateId: "current_prompt",
      isModified: false
    });
  };

  // Add form watch to track content changes
  useEffect(() => {
    const subscription = form.watch((value, { name, type }) => {
      if (name === "promptContent" && type === "change") {
        onPromptChange?.({
          content: value.promptContent,
          templateId: selectedPreset,
          isModified: value.promptContent !== originalContent
        });
      }
    });
    return () => subscription.unsubscribe();
  }, [form, selectedPreset, originalContent, onPromptChange]);

  if (isLoading) {
    return (
      <div>
        <div className="flex items-center space-x-2 mb-6">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-6 w-6 rounded-full" />
        </div>

        <div className="space-y-6">
          <div>
            <div className="flex items-center space-x-3">
              <Skeleton className="h-11 w-[400px] rounded-[12px]" />
              <Skeleton className="h-11 w-24 rounded-[12px]" />
            </div>
          </div>

          <div className="w-full">
            <Skeleton className="h-[400px] w-full rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center space-x-2 mb-6">
        <h3 className="text-sm font-medium">Custom Prompt</h3>
        <HeaderTooltip text="Customize the prompt instructions for your guru" />
      </div>

      <div className="space-y-6">
        <div>
          <div className="flex items-center space-x-2">
            <Select value={selectedPreset} onValueChange={handlePresetChange}>
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
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Textarea
                    {...field}
                    className="min-h-[400px] font-mono text-sm resize-none"
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
