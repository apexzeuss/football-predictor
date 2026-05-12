export default async function handler(request, response) {
  const apiKey = process.env.FOOTBALL_API_KEY || process.env.VITE_FOOTBALL_API_KEY
  const { date, timezone = 'UTC' } = request.query

  if (!apiKey) {
    return response.status(500).json({ errors: { config: 'Football API key is not configured.' }, response: [] })
  }

  if (!date) {
    return response.status(400).json({ errors: { date: 'Date is required.' }, response: [] })
  }

  const upstream = await fetch(
    `https://v3.football.api-sports.io/fixtures?date=${encodeURIComponent(date)}&timezone=${encodeURIComponent(timezone)}`,
    { headers: { 'x-apisports-key': apiKey } }
  )

  const payload = await upstream.json()

  response.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
  return response.status(upstream.status).json(payload)
}
