export async function POST() {
  return Response.json(
    {
      error: "This endpoint is deprecated. Use /api/chat/ for SSE generation.",
    },
    { status: 410 },
  );
}
