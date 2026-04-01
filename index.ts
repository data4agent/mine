import { definePluginEntry, type AnyAgentTool, type OpenClawPluginApi } from "./api.js";
import {
  createCheckStatusTool,
  createMainWorkerTool,
  createRunOnceTool,
  createRunLoopTool,
  createHeartbeatTool,
  createExportCoreSubmissionsTool,
  createListDatasetsTool,
  createPauseTool,
  createProcessTaskFileTool,
  createResumeTool,
  createStartWorkingTool,
  createStopTool,
} from "./src/tools.js";

export default definePluginEntry({
  id: "mine",
  name: "Mine",
  description: "Runs mine/social-data-crawler jobs from OpenClaw tools and worker triggers.",
  register(api: OpenClawPluginApi) {
    api.registerTool(createStartWorkingTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createCheckStatusTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createListDatasetsTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createPauseTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createResumeTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createStopTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createMainWorkerTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createHeartbeatTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createRunOnceTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createRunLoopTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createProcessTaskFileTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createExportCoreSubmissionsTool(api) as unknown as AnyAgentTool, {
      optional: true,
    });
  },
});
