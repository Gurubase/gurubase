"use client";

import { useEffect, useState, useRef } from "react";
import { getSettings } from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";
import { useRouter, usePathname } from "next/navigation";

const ConfigurationCheck = () => {
  const [isCheckingConfig, setIsCheckingConfig] = useState(true);
  const [aiModelProvider, setAiModelProvider] = useState("OPENAI");
  const [isApiKeyValid, setIsApiKeyValid] = useState(true);
  const [isOllamaUrlValid, setIsOllamaUrlValid] = useState(true);
  const [isEmbeddingModelValid, setIsEmbeddingModelValid] = useState(true);
  const [isBaseModelValid, setIsBaseModelValid] = useState(true);
  const router = useRouter();
  const pathname = usePathname();
  const activeToastRef = useRef(false);

  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  const showConfigToast = (message) => {
    if (activeToastRef.current) return;

    activeToastRef.current = true;
    CustomToast({
      message,
      duration: Infinity,
      variant: "error",
      action: {
        label: "Configure Settings",
        onClick: () => {
          activeToastRef.current = false;
          router.push("/settings");
        }
      },
      onClose: () => {
        activeToastRef.current = false;
      }
    });
  };

  const checkConfiguration = async () => {
    if (!isSelfHosted) {
      setIsCheckingConfig(false);
      return;
    }

    try {
      const settings = await getSettings();

      if (settings?.ai_model_provider === "OLLAMA") {
        setAiModelProvider("OLLAMA");
        setIsOllamaUrlValid(settings?.is_ollama_url_valid ?? false);
        setIsEmbeddingModelValid(
          settings?.is_ollama_embedding_model_valid ?? false
        );
        setIsBaseModelValid(settings?.is_ollama_base_model_valid ?? false);

        if (!settings?.is_ollama_url_valid) {
          showConfigToast(
            "Ollama server is inaccessible. Please verify the server status."
          );
        } else if (
          !settings?.is_ollama_embedding_model_valid ||
          !settings?.is_ollama_base_model_valid
        ) {
          showConfigToast(
            "Cannot access the required Ollama models. Check their status on the Settings page."
          );
        }
      } else {
        setAiModelProvider("OPENAI");
        setIsApiKeyValid(settings?.is_openai_key_valid ?? false);

        if (!settings?.is_openai_key_valid) {
          showConfigToast("Configure a valid OpenAI API Key to create a Guru.");
        }
      }
    } catch (error) {
      if (!activeToastRef.current) {
        CustomToast({
          message: "Failed to check configuration status.",
          variant: "error",
          duration: 5000,
          onClose: () => {
            activeToastRef.current = false;
          }
        });
      }
    } finally {
      setIsCheckingConfig(false);
    }
  };

  // Run check on initial load and pathname changes
  useEffect(() => {
    // Skip check if we're already on the settings page
    if (pathname === "/settings") {
      activeToastRef.current = false;
      return;
    }

    checkConfiguration();
  }, [pathname, isSelfHosted, router]);

  // This component doesn't render anything visible
  return null;
};

export default ConfigurationCheck;
