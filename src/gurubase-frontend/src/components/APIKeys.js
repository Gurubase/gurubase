"use client";

import { CopyIcon } from "@radix-ui/react-icons";
import { format, parseISO } from "date-fns";
import { Check, Eye, EyeOff, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createApiKey, deleteApiKey } from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";
import { SolarTrashBinTrashBold } from "@/components/Icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";

const APIKeys = ({ initialApiKeys = [] }) => {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState(null);
  const [visibleKeys, setVisibleKeys] = useState({});
  const [name, setName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [copied, setCopied] = useState(null);
  const router = useRouter();

  const apiKeys = Array.isArray(initialApiKeys) ? initialApiKeys : [];

  const toggleKeyVisibility = (id) => {
    setVisibleKeys((prev) => {
      const newState = prev[id] ? {} : { [id]: true };

      return newState;
    });
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(text);
      setTimeout(() => setCopied(null), 2000);
    } catch (_error) {
      // Failed to copy
    }
  };

  const handleDeleteClick = (key) => {
    setKeyToDelete(key);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    setIsDeleting(true);
    try {
      const formData = new FormData();

      formData.append("id", keyToDelete.key);
      await deleteApiKey(formData);
      router.refresh();
    } catch (_error) {
      // Error handling silently failed
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
      setKeyToDelete(null);
    }
  };

  async function handleCreateSubmit(e) {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData();

      formData.append("name", name);
      const result = await createApiKey(formData);

      if (!result.key) {
        CustomToast({
          message: result.message,
          variant: "error"
        });
      }
      setName("");
      setShowCreateDialog(false);
      router.refresh();
    } catch (error) {
      CustomToast({
        message: "There was an error creating your API key",
        variant: "error"
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="flex justify-center items-center px-16 guru-sm:px-0 w-full flex-grow guru-sm:max-w-full polygon-fill">
      <div className="guru-md:max-w-[870px] guru-lg:max-w-[1180px] w-full gap-4 h-full">
        <div className="grid grid-cols-1 h-full">
          <div className="bg-white shadow-md guru-sm:border-none border-l border-r guru-lg:border-r-0 border-solid border-neutral-200">
            <div className="block guru-sm:hidden border-r border-gray-200">
              <div className="h-full polygon-fill bg-repeat opacity-[0.02]" />
            </div>

            <section className="bg-white border-gray-200">
              <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h1 className="text-[20px] font-semibold text-[#191919] font-inter mb-2">
                      API Keys
                    </h1>
                    <p className="text-[14px] font-normal text-[#6D6D6D] font-inter">
                      Manage your API keys for accessing the Gurubase API.
                    </p>
                  </div>
                  <div>
                    <Button
                      className="rounded-lg bg-gray-800 text-white hover:bg-gray-700"
                      size="lg"
                      onClick={() => setShowCreateDialog(true)}>
                      Create API Key
                    </Button>
                  </div>
                </div>

                <div className="rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow key="header-row">
                        <TableHead className="w-[20%]">Name</TableHead>
                        <TableHead className="w-[50%]">API Key</TableHead>
                        <TableHead className="w-[20%]">Created</TableHead>
                        <TableHead className="w-[10%]">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {apiKeys.length === 0 ? (
                        <TableRow key="empty-row">
                          <TableCell className="h-32 text-center" colSpan={4}>
                            <div className="flex flex-col items-center justify-center text-[#6D6D6D]">
                              <p className="text-sm text-[#6D6D6D]">
                                No API keys found
                              </p>
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : (
                        apiKeys.map((key) => (
                          <TableRow key={key.id}>
                            <TableCell className="font-medium">
                              {key.name}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <span className="relative rounded bg-gray-50 px-[0.5rem] py-[0.3rem] font-mono text-sm min-w-[300px] text-[#191919]">
                                  {visibleKeys[key.id]
                                    ? key.key
                                    : `gb-${"*".repeat(26)}${key.key.slice(-4)}`}
                                </span>
                                <div className="flex items-center gap-0.2">
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    onClick={() => toggleKeyVisibility(key.id)}>
                                    {visibleKeys[key.id] ? (
                                      <EyeOff className="h-4 w-4" />
                                    ) : (
                                      <Eye className="h-4 w-4" />
                                    )}
                                  </Button>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    onClick={() => copyToClipboard(key.key)}>
                                    {copied === key.key ? (
                                      <Check className="h-4 w-4" />
                                    ) : (
                                      <CopyIcon className="h-4 w-4" />
                                    )}
                                  </Button>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              {key.date_created ? (
                                format(
                                  parseISO(key.date_created),
                                  "MMM d, yyyy 'at' h:mm a"
                                )
                              ) : (
                                <span className="text-[#6D6D6D]">-</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <Button
                                size="icon"
                                variant="ghost"
                                onClick={() => handleDeleteClick(key)}>
                                <Trash2 className="h-4 w-4 text-[#DC2626]" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader className="space-y-1.5">
            <DialogTitle className="text-xl font-semibold text-[#191919] font-inter">
              New API Key
            </DialogTitle>
            <DialogDescription className="text-sm text-[#6D6D6D] font-normal">
              Name your key to start using the API
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit}>
            <div className="py-4">
              <Input
                required
                className="h-12"
                id="name"
                placeholder="e.g. Production API Key"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button
                className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
                type="button"
                variant="outline"
                onClick={() => setShowCreateDialog(false)}>
                Cancel
              </Button>
              <Button
                className="h-12 px-6 justify-center items-center rounded-lg bg-gray-800 hover:bg-gray-700 text-white"
                disabled={isLoading || !name.trim()}
                type="submit">
                {isLoading ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-[400px] p-0">
          <div className="p-6 text-center">
            <DialogHeader>
              <div className="mx-auto mb-4 h-[60px] w-[60px] rounded-full text-gray-600">
                <SolarTrashBinTrashBold className="h-full w-full" />
              </div>
              <DialogTitle className="text-base font-semibold text-center text-[#191919] font-inter">
                You are about to remove the API Key
              </DialogTitle>
              <DialogDescription className="text-[14px] text-[#6D6D6D] text-center font-inter font-normal">
                If you confirm, the API key will be removed.
              </DialogDescription>
            </DialogHeader>
            <div className="mt-6 flex flex-col gap-2">
              <Button
                className="h-12 px-6 justify-center items-center rounded-lg bg-[#DC2626] hover:bg-red-700 text-white"
                disabled={isDeleting}
                onClick={handleDeleteConfirm}>
                {isDeleting ? (
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Deleting...</span>
                  </div>
                ) : (
                  "Delete"
                )}
              </Button>
              <Button
                className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
};

export default APIKeys;
