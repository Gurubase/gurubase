"use client";

import { useState, useEffect } from "react";
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
import { Loader2 } from "lucide-react";

// Form validation schema
const formSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address" }),
  docsRootUrl: z.string().url({ message: "Please enter a valid URL" }),
  githubLink: z.string().optional(),
  useCase: z.string().optional()
});

const GuruCreationForm = ({
  source = "unknown",
  onSubmit: externalOnSubmit,
  defaultEmail = "",
  isLoading
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

  // Update email field when defaultEmail changes
  useEffect(() => {
    if (defaultEmail) {
      form.setValue("email", defaultEmail);
    }
  }, [defaultEmail]);

  // Handle form submission
  const handleSubmit = async (data) => {
    setIsSubmitting(true);
    try {
      // Add source to the data
      const submissionData = {
        ...data,
        source
      };

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

  if (isLoading) {
    return (
      <div className="w-full flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full w-full mx-auto p-6 bg-white rounded-lg">
      <div className="h-full flex guru-sm:flex-col">
        <div className="w-1/2 pr-6 guru-sm:w-full guru-sm:pr-0">
          <h3 className="text-xl font-semibold mb-2">Guru Creation Request</h3>
          <p className="text-gray-600 mb-6 guru-sm:text-[16px] text-sm">
            Currently, only the Gurubase team can create a Guru. For this
            reason, we evaluate all Guru creation requests and get back to you
            via email as quickly as possible. We highly recommend filling out
            the Use Case section, as this helps us prioritize creation requests.
          </p>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-5">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <div>
                      <FormLabel>Email</FormLabel>
                      <FormDescription className="mt-1">
                        We'll use this email to contact you about your guru.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Input
                        className="guru-sm:text-[16px] text-sm"
                        placeholder="your.email@example.com"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="docsRootUrl"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <div>
                      <FormLabel>URL</FormLabel>
                      <FormDescription className="mt-1">
                        The documentation or the homepage of the product for
                        which you want to create a Guru.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Input
                        className="guru-sm:text-[16px] text-sm"
                        placeholder="https://docs.example.com"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="githubLink"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <div>
                      <FormLabel>GitHub Repository (Optional)</FormLabel>
                      <FormDescription className="mt-1">
                        Link to your open source GitHub repository.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Input
                        className="guru-sm:text-[16px] text-sm"
                        placeholder="https://github.com/username/repository"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="useCase"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <div>
                      <FormLabel>Use Case (Optional)</FormLabel>
                      <FormDescription className="mt-1">
                        Provide additional context about your use case.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Textarea
                        placeholder="Describe how you plan to use this guru..."
                        className="min-h-[100px] guru-sm:text-[16px] text-sm"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="pt-0">
                <Button
                  type="submit"
                  className="w-full"
                  size="lgRounded"
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
