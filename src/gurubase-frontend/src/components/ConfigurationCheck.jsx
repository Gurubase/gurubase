"use client";

import { useEffect, useState, useRef } from "react";
import { getSettings } from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";
import { useRouter, usePathname } from "next/navigation";
import { toast } from "sonner";

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

  const clearToast = () => {
    activeToastRef.current = false;
    toast.dismiss();
  };

  const checkConfiguration = async () => {
    if (!isSelfHosted) {
      setIsCheckingConfig(false);
      return;
    }

    try {
      const settings = await getSettings();
      let isConfigValid = false;

      if (settings?.ai_model_provider === "OLLAMA") {
        setAiModelProvider("OLLAMA");
        const isUrlValid = settings?.is_ollama_url_valid ?? false;
        const isEmbeddingValid =
          settings?.is_ollama_embedding_model_valid ?? false;
        const isBaseValid = settings?.is_ollama_base_model_valid ?? false;

        setIsOllamaUrlValid(isUrlValid);
        setIsEmbeddingModelValid(isEmbeddingValid);
        setIsBaseModelValid(isBaseValid);

        if (!isUrlValid) {
          showConfigToast(
            "Ollama server is inaccessible. Please verify the server status."
          );
        } else if (!isEmbeddingValid || !isBaseValid) {
          showConfigToast(
            "Cannot access the required Ollama models. Check their status on the Settings page."
          );
        } else {
          isConfigValid = true;
          clearToast();
        }
      } else {
        setAiModelProvider("OPENAI");
        const isKeyValid = settings?.is_openai_key_valid ?? false;
        setIsApiKeyValid(isKeyValid);

        if (!isKeyValid) {
          showConfigToast("Configure a valid OpenAI API Key to use Gurubase.");
        } else {
          isConfigValid = true;
          clearToast();
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

  useEffect(() => {
    if (pathname === "/settings") {
      activeToastRef.current = false;
      return;
    }

    checkConfiguration();
  }, [pathname, isSelfHosted, router]);

  return null;
};

export default ConfigurationCheck;
