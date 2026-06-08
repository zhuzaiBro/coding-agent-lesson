import { AppShell } from "@/components/shell/AppShell";
import { SandpackView } from "@/components/preview/SandpackView";
import { WorkspaceHydrator } from "@/components/shell/WorkspaceHydrator";

export default function Page() {
  return (
    <WorkspaceHydrator>
      <AppShell>
        <SandpackView />
      </AppShell>
    </WorkspaceHydrator>
  );
}
