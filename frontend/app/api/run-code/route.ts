import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import path from "node:path";
import { getQuest } from "@/lib/quests";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { code, chapterSlug } = body;

    if (typeof code !== "string") {
      return NextResponse.json(
        { error: "Parameter 'code' harus berupa string" },
        { status: 400 },
      );
    }

    const quest = chapterSlug ? getQuest(chapterSlug) : null;
    const requiredNodes = quest?.requiredNodes ?? [];
    const expectedOutputSnippet = quest?.expectedOutputSnippet ?? "";

    const runnerPayload = JSON.stringify({
      code,
      requiredNodes,
      expectedOutputSnippet,
    });

    const scriptPath = path.join(process.cwd(), "tools", "ast_runner.py");

    const result = await new Promise<string>((resolve, reject) => {
      const child = spawn("python3", [scriptPath], {
        stdio: ["pipe", "pipe", "pipe"],
      });

      let stdoutData = "";
      let stderrData = "";

      child.stdout.on("data", (chunk) => {
        stdoutData += chunk.toString("utf-8");
      });

      child.stderr.on("data", (chunk) => {
        stderrData += chunk.toString("utf-8");
      });

      child.on("error", (err) => {
        reject(err);
      });

      child.on("close", (code) => {
        if (code !== 0 && !stdoutData) {
          reject(new Error(`Runner error code ${code}: ${stderrData}`));
        } else {
          resolve(stdoutData);
        }
      });

      child.stdin.write(runnerPayload);
      child.stdin.end();
    });

    const parsed = JSON.parse(result);
    return NextResponse.json(parsed);
  } catch (error: any) {
    console.error("API /api/run-code error:", error);
    return NextResponse.json(
      {
        success: false,
        stdout: "",
        stderr: error?.message || "Terjadi kesalahan internal pada server runner Python.",
        ast: {
          syntaxValid: false,
          syntaxError: null,
          nodesFound: [],
          requiredNodes: [],
          missingNodes: [],
          hasAllRequiredNodes: false,
          astTree: "",
        },
        passed: false,
        feedback: "Gagal memproses kode pada backend Python.",
      },
      { status: 500 },
    );
  }
}
