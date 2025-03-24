import { Eye, EyeOff } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import newQuestionIcon from "@/assets/images/new-question.svg";
import { CheckCircleIcon, CloseCircleIcon } from "@/components/Icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SecretInput = ({
  value,
  onChange,
  placeholder,
  isValid,
  hasExisting,
  isEditing,
  maskedValue,
  onStartEditing,
  validMessage,
  invalidMessage,
  className = ""
}) => {
  const [showSecret, setShowSecret] = useState(false);

  console.table({
    hasExisting,
    isEditing,
    isValid,
    value,
    maskedValue,
    placeholder,
    onChange,
    onStartEditing,
    validMessage,
    invalidMessage,
    className
  });

  // Initial readonly state
  if (!isEditing) {
    return (
      <div>
        <div
          className={`flex-1 h-12 px-3 py-2 border rounded-lg bg-white flex items-center justify-between ${
            hasExisting && isValid && !isEditing
              ? "border-[#16A34A]"
              : hasExisting && !isValid && !isEditing
                ? "border-[#DC2626]"
                : "border-[#E2E2E2]"
          }`}>
          <div className="flex flex-col justify-center">
            <span className="text-sm font-mono text-[#6D6D6D]">
              {maskedValue || "No value"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              className="h-8 w-8 hover:bg-gray-50"
              size="icon"
              title="Edit"
              type="button"
              variant="ghost"
              onClick={onStartEditing}>
              <Image
                alt="Edit"
                className="text-gray-500"
                height={18}
                src={newQuestionIcon}
                width={18}
              />
            </Button>
          </div>
        </div>
        {hasExisting && isValid && !isEditing && (
          <div className="flex items-center gap-1 mt-2">
            <CheckCircleIcon />
            <span className="text-[12px] font-normal text-[#16A34A] font-inter">
              {validMessage}
            </span>
          </div>
        )}
        {hasExisting && !isValid && !isEditing && (
          <div className="flex items-center gap-1 mt-2">
            <CloseCircleIcon className="text-[#DC2626]" />
            <span className="text-[12px] font-inter font-normal text-[#DC2626]">
              {invalidMessage}
            </span>
          </div>
        )}
      </div>
    );
  }

  // Edit state
  return (
    <div>
      <div className="relative">
        <Input
          autoComplete="new-password"
          className={`h-12 pr-10 font-mono text-sm text-[#6D6D6D] border ${
            hasExisting && isValid && !isEditing
              ? "border-[#16A34A] ring-0 focus:ring-0 focus-visible:ring-0"
              : hasExisting && !isValid && !isEditing
                ? "border-[#DC2626] ring-0 focus:ring-0 focus-visible:ring-0"
                : "border-[#E2E2E2]"
          } ${className}`}
          data-lpignore="true"
          placeholder={placeholder}
          type={showSecret ? "text" : "password"}
          value={value}
          onChange={onChange}
        />
        {(value.length > 0 || (hasExisting && isValid)) && (
          <button
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            type="button"
            onClick={() => setShowSecret(!showSecret)}>
            {showSecret ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default SecretInput;
