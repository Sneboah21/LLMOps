import React from "react";
import { Bell, Shield, Sparkles } from "lucide-react";
import { AppLayout } from "@/layouts/AppLayout";
import { Card } from "@/components/app/Card";
import { EmptyState } from "@/components/app/EmptyState";
import { PageContainer } from "@/components/app/PageContainer";

const settingsSections = [
  {
    title: "Profile preferences",
    description: "Placeholder space for user profile and workspace personalization.",
    icon: Sparkles,
  },
  {
    title: "Notifications",
    description: "Later you can connect email or in-app alerts for document events.",
    icon: Bell,
  },
  {
    title: "Security",
    description: "Reserved for password updates, tokens, and future session controls.",
    icon: Shield,
  },
];

export const SettingsPage: React.FC = () => {
  return (
    <AppLayout title="Settings">
      <PageContainer>
        <div className="grid gap-4 lg:grid-cols-3">
          {settingsSections.map(({ title, description, icon: Icon }) => (
            <Card key={title} className="space-y-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-200">
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">{title}</h2>
                <p className="mt-2 text-sm text-slate-400">{description}</p>
              </div>
            </Card>
          ))}
        </div>

        <EmptyState
          title="Settings integrations come next"
          description="This page is intentionally UI-only for now, with space reserved for backend-connected preferences later."
        />
      </PageContainer>
    </AppLayout>
  );
};
