"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
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
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { CustomToast } from "@/components/CustomToast";

// Form validation schema
const formSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address" }),
  githubLink: z
    .string()
    .url({ message: "Please enter a valid URL" })
    .refine((url) => url.includes("github.com"), {
      message: "Please enter a valid GitHub URL"
    }),
  docsRootUrl: z.string().url({ message: "Please enter a valid URL" }),
  useCase: z.string().optional()
});

const GuruCreationForm = ({
  source = "unknown",
  onSubmit: externalOnSubmit
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize form with react-hook-form
  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      githubLink: "",
      docsRootUrl: "",
      useCase: ""
    }
  });

  // Handle form submission
  const handleSubmit = async (data) => {
    setIsSubmitting(true);
    try {
      // Add source to the data
      const submissionData = {
        ...data,
        source
      };

      console.log("Form submitted with data:", submissionData);

      // Call external onSubmit if provided
      if (externalOnSubmit) {
        await externalOnSubmit(submissionData);
      }

      // Show success message
      CustomToast({
        message: "Guru creation request submitted successfully!",
        variant: "success"
      });

      // Reset form
      form.reset();
    } catch (error) {
      CustomToast({
        message: "Failed to submit guru creation request. Please try again.",
        variant: "error"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full mx-auto p-6 bg-white rounded-lg">
      <div className="flex guru-sm:flex-col">
        <div className="w-1/2 pr-6 guru-sm:w-full guru-sm:pr-0">
          <h2 className="text-2xl font-semibold mb-6">Create New Guru</h2>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-6">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input placeholder="your.email@example.com" {...field} />
                    </FormControl>
                    <FormDescription>
                      We'll use this email to contact you about your guru.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="githubLink"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>GitHub Repository</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="https://github.com/username/repository"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Link to your open source GitHub repository.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="docsRootUrl"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Documentation Root URL</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="https://docs.example.com"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The root URL of your project documentation.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="useCase"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Use Case (Optional)</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Describe how you plan to use this guru..."
                        className="min-h-[100px]"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Provide additional context about your use case.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="pt-4">
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting}>
                  {isSubmitting ? "Creating..." : "Create Guru"}
                </Button>
              </div>
            </form>
          </Form>

          {/* Hidden field to track source */}
          <div className="hidden">Source: {source}</div>
        </div>
        <div className="w-1/2 guru-sm:w-full guru-sm:mt-6">
          {/* Right column content can be added here */}
        </div>
      </div>
    </div>
  );
};

export default GuruCreationForm;
