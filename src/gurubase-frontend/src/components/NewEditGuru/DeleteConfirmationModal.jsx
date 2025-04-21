import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog";
import { Button } from "@/components/ui/button";
import { SolarTrashBinTrashBold } from "@/components/Icons";

export const DeleteConfirmationModal = ({ isOpen, onOpenChange, onDelete }) => {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[400px] p-0">
        <div className="p-6 text-center">
          <DialogHeader>
            <div className="mx-auto mb-4 h-[60px] w-[60px] rounded-full text-gray-600">
              <SolarTrashBinTrashBold className="h-full w-full" />
            </div>
            <DialogTitle className="text-base font-semibold text-center text-[#191919] font-inter">
              You are about to remove the Guru
            </DialogTitle>
            <DialogDescription className="text-[14px] text-[#6D6D6D] text-center font-inter font-normal">
              If you confirm, the Guru will be removed.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-6 flex flex-col gap-2">
            <Button
              className="h-12 px-6 justify-center items-center rounded-lg bg-[#DC2626] hover:bg-red-700 text-white"
              onClick={onDelete}>
              Delete
            </Button>
            <Button
              className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
              variant="outline"
              onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
