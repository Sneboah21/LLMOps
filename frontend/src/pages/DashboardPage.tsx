// import React from "react";
// import { ArrowRight, MessageSquarePlus } from "lucide-react";
// import { Link } from "react-router-dom";
// import { AppLayout } from "@/layouts/AppLayout";
// import { Card } from "@/components/app/Card";
// import { PageContainer } from "@/components/app/PageContainer";
// import { PrimaryButton } from "@/components/app/PrimaryButton";
// import { mockSessions } from "@/utils/mock-data";

// export const DashboardPage: React.FC = () => {
//   return (
//     <AppLayout title="Dashboard">
//       <PageContainer>
//         <Card glow className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
//           <div>
//             <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
//               Overview
//             </p>
//             <h2 className="mt-2 text-2xl font-semibold text-white">
//               Your recent document sessions
//             </h2>
//             <p className="mt-2 max-w-2xl text-sm text-slate-400">
//               This placeholder dashboard gives you a clean starting point for
//               wiring session lists, uploads, and chat actions later.
//             </p>
//           </div>
//           <Link to="/chat">
//             <PrimaryButton>
//               <MessageSquarePlus className="h-4 w-4" />
//               New Chat
//             </PrimaryButton>
//           </Link>
//         </Card>

//         <div className="grid gap-4 lg:grid-cols-3">
//           {mockSessions.map((session) => (
//             <Card key={session.id} className="flex flex-col gap-4">
//               <div className="flex items-start justify-between gap-3">
//                 <div>
//                   <h3 className="text-lg font-semibold text-white">
//                     {session.title}
//                   </h3>
//                   <p className="mt-2 text-sm text-slate-400">
//                     {session.summary}
//                   </p>
//                 </div>
//                 <span className="rounded-2xl border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
//                   {session.documentCount} docs
//                 </span>
//               </div>

//               <div className="mt-auto flex items-center justify-between text-sm text-slate-500">
//                 <span>{session.updatedAt}</span>
//                 <Link
//                   to={`/chat/${session.id}`}
//                   className="inline-flex items-center gap-2 text-cyan-300 transition hover:text-cyan-200"
//                 >
//                   Open
//                   <ArrowRight className="h-4 w-4" />
//                 </Link>
//               </div>
//             </Card>
//           ))}
//         </div>
//       </PageContainer>
//     </AppLayout>
//   );
// };


import React, { useState } from "react";
import { ArrowRight, MessageSquarePlus } from "lucide-react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/layouts/AppLayout";
import { Card } from "@/components/app/Card";
import { EditableSessionName } from "@/components/app/EditableSessionName";
import { PageContainer } from "@/components/app/PageContainer";
import { PrimaryButton } from "@/components/app/PrimaryButton";
import { listSessions } from "@/api/sessions";
import { useRenameSession } from "@/hooks/useRenameSession";

const truncateSessionTitle = (displayName: string): string => {
  return displayName.length > 24 ? `${displayName.slice(0, 24)}...` : displayName;
};

const formatTimestamp = (isoString: string): string => {
  return new Date(isoString).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
};

export const DashboardPage: React.FC = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { data: sessions, isLoading } = useQuery({
    queryKey: ["sessions"],
    queryFn: listSessions,
  });
  const renameMutation = useRenameSession({ onErrorMessage: setErrorMessage });

  return (
    <AppLayout title="Dashboard">
      <PageContainer>
        {errorMessage && (
          <p className="text-sm text-red-400" role="alert">
            {errorMessage}
          </p>
        )}

        <Card
          glow
          className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between"
        >
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
              Overview
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-white">
              Your recent document sessions
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              {sessions && sessions.length > 0
                ? `You have ${sessions.length} session${sessions.length === 1 ? "" : "s"}. Continue a conversation or start a new one.`
                : "Upload documents to start your first chat session."}
            </p>
          </div>
          <Link to="/upload">
            <PrimaryButton>
              <MessageSquarePlus className="h-4 w-4" />
              New Chat
            </PrimaryButton>
          </Link>
        </Card>

        {isLoading && (
          <p className="text-sm text-slate-400">Loading sessions...</p>
        )}

        {!isLoading && sessions && sessions.length === 0 && (
          <Card className="text-center text-sm text-slate-400">
            No sessions yet. Click "New Chat" to upload documents and begin.
          </Card>
        )}

        <div className="grid gap-4 lg:grid-cols-3">
          {sessions?.map((session) => (
            <Card key={session.session_id} className="flex flex-col gap-4">
              <div className="flex items-start justify-between gap-3">
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
                    Backend: {session.backend}
                  </p>
                </div>
                <span className="rounded-2xl border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                  {session.document_count} docs
                </span>
              </div>

              <div className="mt-auto flex items-center justify-between text-sm text-slate-500">
                <span>{formatTimestamp(session.created_at)}</span>
                <Link
                  to={`/chat/${session.session_id}`}
                  className="inline-flex items-center gap-2 text-cyan-300 transition hover:text-cyan-200"
                >
                  Open
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </Card>
          ))}
        </div>
      </PageContainer>
    </AppLayout>
  );
};
