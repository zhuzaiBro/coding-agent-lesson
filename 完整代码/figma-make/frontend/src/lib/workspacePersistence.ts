import type { ProjectVersion } from "@/types/store";
import { useSandpackStore } from "@/store/sandpackStore";

export const WORKSPACE_STORAGE_KEY = "zood-figma-make-workspace";

/** localStorage 体积有限，较早版本只保留元数据，不存 files */
const MAX_VERSIONS_WITH_FILES = 8;

export function trimVersionsForStorage(
  versions: ProjectVersion[],
): ProjectVersion[] {
  if (versions.length <= MAX_VERSIONS_WITH_FILES) return versions;
  const keepFromIndex = versions.length - MAX_VERSIONS_WITH_FILES;
  return versions.map((v, i) => {
    if (i < keepFromIndex && v.files) {
      return { ...v, files: null };
    }
    return v;
  });
}

export function getLatestVersionWithFiles(
  versions: ProjectVersion[],
): ProjectVersion | null {
  for (let i = versions.length - 1; i >= 0; i--) {
    const v = versions[i];
    if (v.files && Object.keys(v.files).length > 0) {
      return v;
    }
  }
  return null;
}

/** 从版本快照恢复 Sandpack 预览 */
export function restoreSandpackFromVersion(version: ProjectVersion): boolean {
  if (!version.files || Object.keys(version.files).length === 0) {
    return false;
  }
  const { applyAssembledFiles, setViewMode } = useSandpackStore.getState();
  applyAssembledFiles(version.files, { compileChecked: true });
  setViewMode("preview");
  return true;
}

export function restoreSandpackFromVersions(versions: ProjectVersion[]): boolean {
  const latest = getLatestVersionWithFiles(versions);
  if (!latest) return false;
  return restoreSandpackFromVersion(latest);
}
