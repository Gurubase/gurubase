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
import { Loader2, Sparkles, ClipboardCheck, Rocket, Zap } from "lucide-react";

// Form validation schema
const formSchema = z.object({
  name: z.string().min(1, { message: "Name is required" }),
  email: z.string().email({ message: "Please enter a valid email address" }),
  docsRootUrl: z.string().url({ message: "Please enter a valid URL" }),
  githubLink: z.string().optional(),
  useCase: z.string().optional()
});

const GuruCreationForm = ({
  source = "unknown",
  onSubmit: externalOnSubmit,
  defaultEmail = "",
  defaultName = "",
  isLoading
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showThankYou, setShowThankYou] = useState(false);

  // Initialize form with react-hook-form
  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
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

  // Update name field when defaultName changes
  useEffect(() => {
    if (defaultName) {
      form.setValue("name", defaultName);
    }
  }, [defaultName]);

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

      // Show thank you section
      setShowThankYou(true);

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

  // Thank you component shown after submission
  if (showThankYou) {
    return (
      <div className="h-full w-full mx-auto p-6 bg-white rounded-lg">
        <div className="text-center py-10">
          <div className="mb-6">
            <div className="w-20 h-20 bg-green-100 flex items-center justify-center rounded-full mx-auto mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold mb-2">Your Guru is on its way!</h3>
            <p className="text-gray-600">
              We're reviewing your request and will reach out within 24 hours.
            </p>
          </div>
          
          <div className="flex flex-col space-y-5 max-w-md mx-auto mb-8">
            <a 
              href="https://discord.com/invite/9CMRSQPqx6" 
              target="_blank" 
              rel="noopener noreferrer"
              className="py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-700 text-white font-medium rounded-lg hover:from-blue-700 hover:to-indigo-800 shadow-md hover:shadow-lg transition-all flex items-center justify-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 71 55" fill="currentColor">
                <path d="M60.1045 4.8978C55.5792 2.8214 50.7265 1.2916 45.6527 0.41542C45.5603 0.39851 45.468 0.440769 45.4204 0.525289C44.7963 1.6353 44.105 3.0834 43.6209 4.2216C38.1637 3.4046 32.7345 3.4046 27.3892 4.2216C26.905 3.0581 26.1886 1.6353 25.5617 0.525289C25.5141 0.443589 25.4218 0.40133 25.3294 0.41542C20.2584 1.2888 15.4057 2.8186 10.8776 4.8978C10.8384 4.9147 10.8048 4.9429 10.7825 4.9795C1.57795 18.7309 -0.943561 32.1443 0.293408 45.3914C0.299005 45.4562 0.335386 45.5182 0.385761 45.5576C6.45866 50.0174 12.3413 52.7249 18.1147 54.5195C18.2071 54.5477 18.305 54.5139 18.3638 54.4378C19.7295 52.5728 20.9469 50.6063 21.9907 48.5383C22.0523 48.4172 21.9935 48.2735 21.8676 48.2256C19.9366 47.4931 18.0979 46.6 16.3292 45.5858C16.1893 45.5041 16.1781 45.304 16.3068 45.2082C16.679 44.9293 17.0513 44.6391 17.4067 44.3461C17.471 44.2926 17.5606 44.2813 17.6362 44.3151C29.2558 49.6202 41.8354 49.6202 53.3179 44.3151C53.3935 44.2785 53.4831 44.2898 53.5502 44.3433C53.9057 44.6363 54.2779 44.9293 54.6529 45.2082C54.7816 45.304 54.7732 45.5041 54.6333 45.5858C52.8646 46.6197 51.0259 47.4931 49.0921 48.2228C48.9662 48.2707 48.9102 48.4172 48.9718 48.5383C50.038 50.6034 51.2554 52.5699 52.5959 54.435C52.6519 54.5139 52.7526 54.5477 52.845 54.5195C58.6464 52.7249 64.529 50.0174 70.6019 45.5576C70.6551 45.5182 70.6887 45.459 70.6943 45.3942C72.1747 30.0791 68.2147 16.7757 60.1968 4.9823C60.1772 4.9429 60.1437 4.9147 60.1045 4.8978ZM23.7259 37.3253C20.2276 37.3253 17.3451 34.1136 17.3451 30.1693C17.3451 26.225 20.1717 23.0133 23.7259 23.0133C27.308 23.0133 30.1626 26.2532 30.1066 30.1693C30.1066 34.1136 27.28 37.3253 23.7259 37.3253ZM47.3178 37.3253C43.8196 37.3253 40.9371 34.1136 40.9371 30.1693C40.9371 26.225 43.7636 23.0133 47.3178 23.0133C50.9 23.0133 53.7545 26.2532 53.6986 30.1693C53.6986 34.1136 50.9 37.3253 47.3178 37.3253Z" />
              </svg>
              Join our Discord community
            </a>
            
            <div className="text-center mt-6">
              <p className="text-gray-700 mb-3">Want to see Gurus in action?</p>
              <a 
                href="https://docs.gurubase.io" 
                target="_blank" 
                rel="noopener noreferrer"
                className="py-4 px-6 bg-indigo-100 text-indigo-700 font-medium rounded-lg hover:bg-indigo-200 transition-all flex items-center justify-center group"
              >
                <span className="relative inline-flex justify-center items-center">
                  <Sparkles className="h-5 w-5 mr-2 text-indigo-500 transition-all duration-300 group-hover:text-yellow-500 group-hover:scale-110 group-hover:rotate-12" />
                  <span className="absolute top-0 left-0 w-full h-full group-hover:animate-ping rounded-full bg-yellow-300 opacity-0 group-hover:opacity-30"></span>
                </span>
                Try "Ask AI" button on Gurubase Docs
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full mx-auto p-6 bg-white rounded-lg">
      <div className="h-full flex guru-sm:flex-col">
        <div className="w-1/2 pr-6 guru-sm:w-full guru-sm:pr-0">
          <h3 className="text-xl font-semibold mb-2">Guru Creation Request</h3>
          <p className="text-gray-600 mb-6 guru-sm:text-[16px] text-sm">
            Tell us about your product, and we'll help you create an AI assistant (Guru) for your content.
          </p>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-5">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <div>
                      <FormLabel>Name</FormLabel>
                    </div>
                    <FormControl>
                      <Input
                        className="guru-sm:text-[16px] text-sm"
                        placeholder="John Doe"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <div>
                      <FormLabel>Email</FormLabel>
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
                        Documentation, help center, knowledge base, or any content you want to turn into an AI assistant.
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
                      <FormLabel>GitHub Repository <span className="text-gray-400 text-xs font-normal">(Optional)</span></FormLabel>
                      <FormDescription className="mt-1">
                        Adding your code helps your Guru provide more accurate, context-aware answers.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Input
                        className="guru-sm:text-[16px] text-sm"
                        placeholder="https://github.com/owner/repository"
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
                      <FormLabel>Use Case <span className="text-gray-400 text-xs font-normal">(Optional)</span></FormLabel>
                    </div>
                    <FormControl>
                      <Textarea
                        placeholder="e.g. We want to embed the 'Ask AI' button in our docs site for faster support."
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
                  {isSubmitting ? "Submitting..." : "Submit Request"}
                </Button>
              </div>
            </form>
          </Form>

          {/* Hidden field to track source */}
          <div className="hidden">Source: {source}</div>
        </div>
        <div className="w-1/2 guru-sm:w-full guru-sm:mt-6">
          {/* Right column content - Process and Featured Gurus */}
          <div className="bg-white shadow-sm border border-gray-100 p-6 rounded-lg h-full">
            <div className="mb-8">
              <div className="relative pb-2">
                {/* Timeline connecting line */}
                <div className="absolute left-[24px] top-[0px] w-[2px] h-[calc(100%-10px)] bg-blue-50"></div>
                
                {/* Step 1 */}
                <div className="flex items-start mb-10 group">
                  <div className="relative z-10">
                    <div className="w-[48px] h-[48px] rounded-lg bg-blue-50 flex items-center justify-center">
                      <ClipboardCheck className="h-5 w-5 text-blue-600" />
                    </div>
                  </div>
                  <div className="ml-5">
                    <div className="text-blue-500 text-xs font-medium mb-1">STEP 1</div>
                    <div className="font-medium text-gray-700">We'll review it and create your Guru</div>
                    <div className="text-gray-400 text-sm mt-1">Typically within 24 hours</div>
                  </div>
                </div>
                
                {/* Step 2 */}
                <div className="flex items-start mb-10 group">
                  <div className="relative z-10">
                    <div className="w-[48px] h-[48px] rounded-lg bg-indigo-50 border border-indigo-100 shadow-sm flex items-center justify-center">
                      <Rocket className="h-5 w-5 text-indigo-600" />
                    </div>
                  </div>
                  <div className="ml-5">
                    <div className="text-indigo-500 text-xs font-medium mb-1">STEP 2</div>
                    <div className="font-medium text-gray-700">Get access to your custom Guru in a sandbox environment</div>
                    <div className="text-gray-400 text-sm mt-1">Try your AI Assistant with real questions</div>
                  </div>
                </div>
                
                {/* Step 3 */}
                <div className="flex items-start group">
                  <div className="relative z-10">
                    <div className="w-[48px] h-[48px] rounded-lg bg-green-50 border border-green-100 shadow-sm flex items-center justify-center">
                      <Zap className="h-5 w-5 text-green-600" />
                    </div>
                  </div>
                  <div className="ml-5">
                    <div className="text-green-500 text-xs font-medium mb-1">STEP 3</div>
                    <div className="font-medium text-gray-700">Add "Ask AI" button to your site or use with Slack/Discord</div>
                    <div className="text-gray-400 text-sm mt-1">Your users get instant, reference-backed answers</div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="pt-5 border-t border-gray-100">
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-lg p-4 relative border border-gray-100 shadow-sm">
                  <div className="flex mb-2">
                    <div className="text-blue-400 opacity-60 mr-2 flex-shrink-0 self-start mt-1">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M10.2924 7.93139C8.19075 9.02442 7.14001 10.5653 7.14001 12.5537C7.14001 15.0529 8.87988 16.3025 12.3597 16.3025C12.5889 16.3025 12.7814 16.3721 12.9372 16.5113C13.1043 16.6505 13.1878 16.8286 13.1878 17.0456C13.1878 17.4406 12.8865 17.638 12.2837 17.638C8.57764 17.638 6.72461 15.9027 6.72461 12.432C6.72461 9.21997 8.51172 6.65462 12.0859 4.73584L10.2924 7.93139ZM18.2944 7.93139C16.2041 9.02442 15.1589 10.5653 15.1589 12.5537C15.1589 15.0529 16.8933 16.3025 20.3731 16.3025C20.6022 16.3025 20.7948 16.3721 20.9506 16.5113C21.1177 16.6505 21.2012 16.8286 21.2012 17.0456C21.2012 17.4406 20.8999 17.638 20.2971 17.638C16.591 17.638 14.738 15.9027 14.738 12.432C14.738 9.21997 16.5251 6.65462 20.0993 4.73584L18.2944 7.93139Z" fill="currentColor"/>
                      </svg>
                    </div>
                    <p className="text-gray-700 text-sm leading-relaxed">
                      Gurubase has been an excellent tool for the Interoperability Test Bed (ITB), helping improve our documentation and support users effectively. Although still in its early days, it already delivers strong value and is backed by a responsive, supportive team.
                    </p>
                  </div>
                  
                  <div className="flex items-center justify-between pt-3 border-t border-gray-200">
                    <div className="flex items-center">
                      <div className="mr-2 flex-shrink-0">
                        <img 
                          src="https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/costas_7ed1404c1a.jpeg" 
                          alt="Costas Simatos" 
                          className="w-10 h-10 rounded-full object-cover border border-gray-200"
                          loading="eager"
                          onError={(e) => {
                            e.target.onerror = null;
                            e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='8' r='5'/%3E%3Cpath d='M20 21a8 8 0 0 0-16 0'/%3E%3C/svg%3E";
                          }}
                        />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">Costas Simatos</p>
                        <p className="text-xs text-gray-600">Team Leader, ITB, European Commission</p>
                      </div>
                    </div>
                    <div className="shrink-0 ml-3">
                      <img 
                        src="https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/itb_guru_logo_21bf97e606.png" 
                        alt="ITB Guru" 
                        className="w-24 h-auto object-contain" 
                        loading="eager"
                        onError={(e) => {
                          e.target.onerror = null;
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GuruCreationForm;
