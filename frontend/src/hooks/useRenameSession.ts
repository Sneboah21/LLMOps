import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { renameSession } from "@/api/sessions";
import type { SessionSummary } from "@/types/api";

interface RenameSessionVariables {
  sessionId: string;
  displayName: string;
}

interface UseRenameSessionOptions {
  onErrorMessage?: (message: string | null) => void;
}

export const useRenameSession = (
  options: UseRenameSessionOptions = {}
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, displayName }: RenameSessionVariables) =>
      renameSession(sessionId, { display_name: displayName }),
    onMutate: ({ sessionId, displayName }) => {
      options.onErrorMessage?.(null);

      const previousSessions =
        queryClient.getQueryData<SessionSummary[]>(["sessions"]) ?? [];

      queryClient.setQueryData<SessionSummary[]>(["sessions"], (current = []) =>
        current.map((session) =>
          session.session_id === sessionId
            ? { ...session, display_name: displayName }
            : session
        )
      );

      return { previousSessions };
    },
    onError: (error, _variables, context) => {
      if (context?.previousSessions) {
        queryClient.setQueryData(["sessions"], context.previousSessions);
      }

      if (isAxiosError(error) && error.response?.data?.detail) {
        options.onErrorMessage?.(String(error.response.data.detail));
      } else {
        options.onErrorMessage?.("Failed to rename session. Please try again.");
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData<SessionSummary[]>(["sessions"], (current = []) =>
        current.map((session) =>
          session.session_id === data.session_id
            ? { ...session, display_name: data.display_name }
            : session
        )
      );
    },
  });
};
