import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog";
import GuruBaseLogo from "@/components/GuruBaseLogo";
import { useAppNavigation } from "@/lib/navigation";
import { usePathname } from "next/navigation";

export default function LoginModal({ isOpen, onClose }) {
  const pathname = usePathname();
  const navigation = useAppNavigation();

  const handleNavigate = (path) => {
    const returnTo = encodeURIComponent(pathname);
    onClose();
    navigation.push(`${path}?returnTo=${returnTo}`);
  };

  useEffect(() => {
    const handleKeyDown = (event) => {
      // Prevent all key strokes
      event.preventDefault();
    };

    if (isOpen) {
      // Prevent scrolling on the background
      document.body.style.overflow = "hidden";
      // Add dim class to main content
      document.querySelector("main")?.classList.add("content-dimmed");
      // Add keydown event listener
      window.addEventListener("keydown", handleKeyDown);
    } else {
      // Re-enable scrolling
      document.body.style.overflow = "auto";
      // Remove dim class from main content
      document.querySelector("main")?.classList.remove("content-dimmed");
      // Remove keydown event listener
      window.removeEventListener("keydown", handleKeyDown);
    }

    return () => {
      // Cleanup
      document.body.style.overflow = "auto";
      document.querySelector("main")?.classList.remove("content-dimmed");
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <Dialog defaultOpen>
      <DialogContent
        className="max-w-md rounded-3xl p-6"
        onClose={onClose}
        onPointerDownOutside={(e) => {
          // Prevent closing when clicking outside
          e.preventDefault();
        }}
        onEscapeKeyDown={(e) => {
          // Prevent closing when pressing Escape
          e.preventDefault();
        }}>
        <div className="flex justify-center p-2">
          <GuruBaseLogo className="h-6 w-auto text-3xl" alt="GuruBase Logo" />
        </div>

        <DialogHeader className="pb-4">
          <DialogTitle className="text-center text-[#191919] text-[18px] font-inter font-semibold">
            Log In to Continue
          </DialogTitle>
        </DialogHeader>

        <div className="flex space-x-3 font-inter font-normal">
          <Button
            variant="outline"
            className="flex-1 rounded-full py-6 text-[14px] font-medium"
            onClick={() => handleNavigate("/api/auth/login")}>
            Log in
          </Button>
          <Button
            className="flex-1 rounded-full bg-[#1c2127] py-6 text-[14px] font-medium"
            onClick={() => handleNavigate("/api/auth/login")}>
            Sign Up
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
