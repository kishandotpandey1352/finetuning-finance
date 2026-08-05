import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getAgentServiceUrl() {
  return (
    process.env.AGENT_SERVICE_URL ??
    process.env.NEXT_PUBLIC_AGENT_SERVICE_URL ??
    "http://localhost:3001"
  );
}

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "anonymous";
}

async function parseAgentServiceResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

export async function POST(request: Request) {
  const requestId = crypto.randomUUID();

  try {
    const body = await request.json();

    const response = await fetch(`${getAgentServiceUrl()}/memory/propose`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-user-id": getUserId(request),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const payload = await parseAgentServiceResponse(response);

    return NextResponse.json(
      {
        requestId,
        ...(typeof payload === "object" && payload !== null ? payload : {}),
      },
      { status: response.status },
    );
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        requestId,
        error:
          error instanceof Error
            ? error.message
            : "Failed to propose memory through agent service.",
      },
      { status: 502 },
    );
  }
}