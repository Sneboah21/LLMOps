// import React from "react";
// import { Clock3, Trash2 } from "lucide-react";
// import { AppLayout } from "@/layouts/AppLayout";
// import { Card } from "@/components/app/Card";
// import { PageContainer } from "@/components/app/PageContainer";
// import { SecondaryButton } from "@/components/app/SecondaryButton";
// import { mockSessions } from "@/utils/mock-data";

// export const SessionHistoryPage: React.FC = () => {
//   return (
//     <AppLayout title="Session History">
//       <PageContainer>
//         <div className="grid gap-4 xl:grid-cols-2">
//           {mockSessions.map((session) => (
//             <Card key={session.id} className="flex flex-col gap-4">
//               <div className="flex items-start justify-between gap-4">
//                 <div>
//                   <h2 className="text-lg font-semibold text-white">
//                     {session.title}
//                   </h2>
//                   <p className="mt-2 text-sm text-slate-400">
//                     {session.summary}
//                   </p>
//                 </div>
//                 <SecondaryButton
//                   onClick={() => {
//                     // TODO: Connect delete session action.
//                   }}
//                 >
//                   <Trash2 className="h-4 w-4" />
//                   Delete
//                 </SecondaryButton>
//               </div>

//               <div className="flex items-center gap-2 text-sm text-slate-500">
//                 <Clock3 className="h-4 w-4" />
//                 {session.updatedAt}
//               </div>
//             </Card>
//           ))}
//         </div>
//       </PageContainer>
//     </AppLayout>
//   );
// };


import React, { useState } from "react";
import { Clock3, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { AppLayout } from "@/layouts/AppLayout";
import { Card } from "@/components/app/Card";
import { EditableSessionName } from "@/components/app/EditableSessionName";
import { PageContainer } from "@/components/app/PageContainer";
import { SecondaryButton } from "@/components/app/SecondaryButton";
import { listSessions, deleteSession } from "@/api/sessions";
import { useRenameSession } from "@/hooks/useRenameSession";

const truncateSessionTitle = (displayName: string): string => {
  return displayName.length > 32 ? `${displayName.slice(0, 32)}...` : displayName;
};

const formatTimestamp = (isoString: string): string => {
  return new Date(isoString).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
};

export const SessionHistoryPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["sessions"],
    queryFn: listSessions,
  });

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => deleteSession(sessionId),
    onMutate: (sessionId) => {
      setErrorMessage(null);
      setDeletingId(sessionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
    onError: (error: unknown) => {
      if (isAxiosError(error) && error.response?.data?.detail) {
        setErrorMessage(String(error.response.data.detail));
      } else {
        setErrorMessage("Failed to delete session. Please try again.");
      }
    },
    onSettled: () => {
      setDeletingId(null);
    },
  });
  const renameMutation = useRenameSession({ onErrorMessage: setErrorMessage });

  return (
    <AppLayout title="Session History">
      <PageContainer>
        {errorMessage && (
          <p className="text-sm text-red-400" role="alert">
            {errorMessage}
          </p>
        )}

        {isLoading && (
          <p className="text-sm text-slate-400">Loading sessions...</p>
        )}

        {!isLoading && sessions && sessions.length === 0 && (
          <Card className="text-center text-sm text-slate-400">
            No sessions found.
          </Card>
        )}

        <div className="grid gap-4 xl:grid-cols-2">
          {sessions?.map((session) => (
            <Card key={session.session_id} className="flex flex-col gap-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-lg font-semibold text-white">
                    <EditableSessionName
                      sessionId={session.session_id}
                      value={truncateSessionTitle(
                        session.display_name || session.session_id
                      )}
                      onSave={async (nextValue) => {
                        await renameMutation.mutateAsync({
                          sessionId: session.session_id,
                          displayName: nextValue,
                        });
                      }}
                    />
                  </div>
                  <p className="mt-2 text-sm text-slate-400">
                    {session.document_count} document
                    {session.document_count === 1 ? "" : "s"} •{" "}
                    {session.message_count} message
                    {session.message_count === 1 ? "" : "s"} •{" "}
                    {session.backend}
                  </p>
                </div>
                <SecondaryButton
                  disabled={deletingId === session.session_id}
                  onClick={() => deleteMutation.mutate(session.session_id)}
                >
                  <Trash2 className="h-4 w-4" />
                  {deletingId === session.session_id
                    ? "Deleting..."
                    : "Delete"}
                </SecondaryButton>
              </div>

              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Clock3 className="h-4 w-4" />
                {formatTimestamp(session.created_at)}
              </div>
            </Card>
          ))}
        </div>
      </PageContainer>
    </AppLayout>
  );
};
