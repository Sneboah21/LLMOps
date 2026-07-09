// import React, { useMemo, useState } from "react";
// import { FileUp, HardDriveUpload } from "lucide-react";
// import { AppLayout } from "@/layouts/AppLayout";
// import { Card } from "@/components/app/Card";
// import { PageContainer } from "@/components/app/PageContainer";
// import { PrimaryButton } from "@/components/app/PrimaryButton";
// import { SecondaryButton } from "@/components/app/SecondaryButton";
// import { mockUploadedFiles } from "@/utils/mock-data";
// import { cn } from "@/lib/utils";

// type RetrievalBackend = "FAISS" | "PageIndex";

// export const UploadPage: React.FC = () => {
//   const [selectedBackend, setSelectedBackend] = useState<RetrievalBackend>("FAISS");
//   const [dragActive, setDragActive] = useState(false);
//   const uploadCount = useMemo(() => mockUploadedFiles.length, []);

//   return (
//     <AppLayout title="Upload">
//       <PageContainer>
//         <Card glow className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
//           <div
//             onDragEnter={() => setDragActive(true)}
//             onDragLeave={() => setDragActive(false)}
//             onDragOver={(event) => event.preventDefault()}
//             onDrop={(event) => {
//               event.preventDefault();
//               setDragActive(false);
//               // TODO: Capture dropped files and connect upload pipeline.
//             }}
//             className={cn(
//               "flex min-h-72 flex-col items-center justify-center rounded-[1.75rem] border border-dashed px-6 text-center transition",
//               dragActive
//                 ? "border-cyan-400/60 bg-cyan-400/10"
//                 : "border-white/15 bg-white/5"
//             )}
//           >
//             <div className="rounded-3xl border border-white/10 bg-slate-950 p-4 text-cyan-300">
//               <FileUp className="h-8 w-8" />
//             </div>
//             <h2 className="mt-5 text-xl font-semibold text-white">
//               Drag and drop files here
//             </h2>
//             <p className="mt-2 max-w-md text-sm text-slate-400">
//               Add PDFs, DOCX, or text files. This is a placeholder upload area
//               with no API integration yet.
//             </p>
//             <SecondaryButton className="mt-5">
//               Browse Files
//             </SecondaryButton>
//           </div>

//           <div className="space-y-4">
//             <div>
//               <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
//                 Retrieval backend
//               </p>
//               <div className="mt-3 grid gap-3">
//                 {(["FAISS", "PageIndex"] as RetrievalBackend[]).map((backend) => (
//                   <button
//                     key={backend}
//                     type="button"
//                     onClick={() => setSelectedBackend(backend)}
//                     className={cn(
//                       "rounded-2xl border px-4 py-3 text-left text-sm transition",
//                       selectedBackend === backend
//                         ? "border-cyan-400/50 bg-cyan-400/10 text-white"
//                         : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
//                     )}
//                   >
//                     <span className="block font-medium">{backend}</span>
//                     <span className="mt-1 block text-xs text-slate-500">
//                       Placeholder selector for future indexing behavior.
//                     </span>
//                   </button>
//                 ))}
//               </div>
//             </div>

//             <Card className="space-y-3 bg-slate-950/70 p-4">
//               <div className="flex items-center justify-between text-sm">
//                 <span className="text-slate-400">Queued files</span>
//                 <span className="text-white">{uploadCount}</span>
//               </div>
//               <PrimaryButton
//                 className="w-full"
//                 onClick={() => {
//                   // TODO: Trigger upload once API integration is ready.
//                 }}
//               >
//                 <HardDriveUpload className="h-4 w-4" />
//                 Upload Files
//               </PrimaryButton>
//             </Card>
//           </div>
//         </Card>

//         <Card className="space-y-4">
//           <div className="flex items-center justify-between">
//             <div>
//               <h2 className="text-lg font-semibold text-white">
//                 Uploaded files
//               </h2>
//               <p className="mt-1 text-sm text-slate-400">
//                 Mock file list for the UI skeleton.
//               </p>
//             </div>
//           </div>

//           <div className="space-y-3">
//             {mockUploadedFiles.map((file) => (
//               <div
//                 key={file.id}
//                 className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 md:flex-row md:items-center md:justify-between"
//               >
//                 <div>
//                   <p className="text-sm font-medium text-white">{file.name}</p>
//                   <p className="text-xs text-slate-500">{file.size}</p>
//                 </div>
//                 <span className="rounded-2xl border border-white/10 px-3 py-1 text-xs text-slate-300">
//                   {file.status}
//                 </span>
//               </div>
//             ))}
//           </div>
//         </Card>
//       </PageContainer>
//     </AppLayout>
//   );
// };


import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { FileUp, HardDriveUpload } from "lucide-react";
import { isAxiosError } from "axios";
import { AppLayout } from "@/layouts/AppLayout";
import { Card } from "@/components/app/Card";
import { PageContainer } from "@/components/app/PageContainer";
import { PrimaryButton } from "@/components/app/PrimaryButton";
import { SecondaryButton } from "@/components/app/SecondaryButton";
import { uploadFiles } from "@/api/upload";
import { cn } from "@/lib/utils";

type RetrievalBackend = "FAISS" | "PageIndex";

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedBackend, setSelectedBackend] =
    useState<RetrievalBackend>("FAISS");
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => uploadFiles(selectedFiles, selectedBackend),
    onSuccess: (data) => {
      navigate(`/chat/${data.session_id}`);
    },
    onError: (error: unknown) => {
      if (isAxiosError(error) && error.response?.data?.detail) {
        setErrorMessage(String(error.response.data.detail));
      } else {
        setErrorMessage("Upload failed. Please try again.");
      }
    },
  });

  const addFiles = (incoming: FileList | null) => {
    if (!incoming || incoming.length === 0) return;
    setErrorMessage(null);
    setSelectedFiles((prev) => [...prev, ...Array.from(incoming)]);
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleUploadClick = () => {
    if (selectedFiles.length === 0) {
      setErrorMessage("Please select at least one file.");
      return;
    }
    setErrorMessage(null);
    mutation.mutate();
  };

  const removeFile = (indexToRemove: number) => {
    setSelectedFiles((prev) =>
      prev.filter((_, index) => index !== indexToRemove)
    );
  };

  return (
    <AppLayout title="Upload">
      <PageContainer>
        <Card glow className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div
            onDragEnter={() => setDragActive(true)}
            onDragLeave={() => setDragActive(false)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              setDragActive(false);
              addFiles(event.dataTransfer.files);
            }}
            className={cn(
              "flex min-h-72 flex-col items-center justify-center rounded-[1.75rem] border border-dashed px-6 text-center transition",
              dragActive
                ? "border-cyan-400/60 bg-cyan-400/10"
                : "border-white/15 bg-white/5"
            )}
          >
            <div className="rounded-3xl border border-white/10 bg-slate-950 p-4 text-cyan-300">
              <FileUp className="h-8 w-8" />
            </div>
            <h2 className="mt-5 text-xl font-semibold text-white">
              Drag and drop files here
            </h2>
            <p className="mt-2 max-w-md text-sm text-slate-400">
              Add PDFs, DOCX, or text files to build your retrieval session.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(event) => addFiles(event.target.files)}
            />

            <SecondaryButton className="mt-5" onClick={handleBrowseClick}>
              Browse Files
            </SecondaryButton>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                Retrieval backend
              </p>
              <div className="mt-3 grid gap-3">
                {(["FAISS", "PageIndex"] as RetrievalBackend[]).map(
                  (backend) => (
                    <button
                      key={backend}
                      type="button"
                      onClick={() => setSelectedBackend(backend)}
                      className={cn(
                        "rounded-2xl border px-4 py-3 text-left text-sm transition",
                        selectedBackend === backend
                          ? "border-cyan-400/50 bg-cyan-400/10 text-white"
                          : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                      )}
                    >
                      <span className="block font-medium">{backend}</span>
                      <span className="mt-1 block text-xs text-slate-500">
                        {backend === "FAISS"
                          ? "Vector similarity search."
                          : "Reasoning-based, vectorless retrieval."}
                      </span>
                    </button>
                  )
                )}
              </div>
            </div>

            <Card className="space-y-3 bg-slate-950/70 p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Queued files</span>
                <span className="text-white">{selectedFiles.length}</span>
              </div>

              {errorMessage && (
                <p className="text-sm text-red-400" role="alert">
                  {errorMessage}
                </p>
              )}

              <PrimaryButton
                className="w-full"
                disabled={mutation.isPending}
                onClick={handleUploadClick}
              >
                <HardDriveUpload className="h-4 w-4" />
                {mutation.isPending ? "Uploading..." : "Upload Files"}
              </PrimaryButton>
            </Card>
          </div>
        </Card>

        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">
                Selected files
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                {selectedFiles.length === 0
                  ? "No files selected yet."
                  : "These files will be uploaded when you click Upload Files."}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-white">
                    {file.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatFileSize(file.size)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="rounded-2xl border border-white/10 px-3 py-1 text-xs text-slate-300 hover:bg-white/10"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </Card>
      </PageContainer>
    </AppLayout>
  );
};