<script setup lang="ts">
import { ref, onMounted } from 'vue'

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS
const API_KEY = import.meta.env.VITE_FOOTBALL_API_KEY

const activeTab = ref('home')
const matches = ref<any[]>([])
const selectedMatch = ref<any>(null)
const contractMatch = ref<any>(null)
const loading = ref(false)
const staking = ref(false)
const creating = ref(false)
const message = ref('')
const messageType = ref('info')

async function getClient() {
  const { createClient, createAccount } = await import('genlayer-js')
  const { studionet } = await import('genlayer-js/chains')
  return createClient({ chain: studionet, account: createAccount() })
}

async function fetchMatches() {
  loading.value = true
  try {
    const today = new Date().toISOString().split('T')[0]
    const res = await fetch(
      `https://v3.football.api-sports.io/fixtures?date=${today}&timezone=UTC`,
      { headers: { 'x-apisports-key': API_KEY } }
    )
    const data = await res.json()
    matches.value = data.response.slice(0, 30)
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

async function selectMatch(match: any) {
  selectedMatch.value = match
  contractMatch.value = null
  activeTab.value = 'predict'
  const matchId = `match_${match.fixture.id}`
  try {
    const client = await getClient()
    const info = await client.readContract({
      address: CONTRACT_ADDRESS,
      functionName: 'get_match',
      args: [matchId]
    })
    const parsed = JSON.parse(info as string)
    if (parsed.home_team) contractMatch.value = parsed
  } catch (e) {
    console.error(e)
  }
}

async function createAndStake(match: any, prediction: string) {
  creating.value = true
  staking.value = true
  message.value = 'Adding match to blockchain...'
  messageType.value = 'info'
  const matchId = `match_${match.fixture.id}`

  try {
    const client = await getClient()

    await client.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: 'create_match',
      args: [matchId, match.teams.home.name, match.teams.away.name, match.league.name, match.fixture.date.split('T')[0]],
      value: 0n,
      leaderOnly: true
    } as any)

    message.value = 'Match added! Placing stake...'

    await client.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: 'stake',
      args: [matchId, prediction, 100, '0xBceFf82Fa1473e28bB00E1A20CCD61ABce0477b2'],
      value: 0n,
      leaderOnly: true
    } as any)

    message.value = 'Stake placed successfully!'
    messageType.value = 'success'
    await selectMatch(match)
  } catch (e) {
    console.error(e)
    message.value = 'Something went wrong. Try again.'
    messageType.value = 'error'
  }
  creating.value = false
  staking.value = false
}

async function stake(prediction: string) {
  if (!selectedMatch.value) return
  staking.value = true
  message.value = 'Placing stake...'
  messageType.value = 'info'
  const matchId = `match_${selectedMatch.value.fixture.id}`

  try {
    const client = await getClient()
    await client.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: 'stake',
      args: [matchId, prediction, 100, '0xBceFf82Fa1473e28bB00E1A20CCD61ABce0477b2'],
      value: 0n,
      leaderOnly: true
    } as any)

    message.value = 'Stake placed successfully!'
    messageType.value = 'success'
    await selectMatch(selectedMatch.value)
  } catch (e) {
    console.error(e)
    message.value = 'Stake failed. Try again.'
    messageType.value = 'error'
  }
  staking.value = false
}

onMounted(fetchMatches)
</script>

<template>
  <div class="app">
    <nav class="navbar">
      <div class="nav-logo">GenPredict</div>
      <div class="nav-tabs">
        <button :class="['nav-tab', activeTab === 'home' ? 'active' : '']" @click="activeTab = 'home'">Home</button>
        <button :class="['nav-tab', activeTab === 'matches' ? 'active' : '']" @click="activeTab = 'matches'; fetchMatches()">Matches</button>
        <button :class="['nav-tab', activeTab === 'predict' ? 'active' : '']" @click="activeTab = 'predict'">Predict</button>
      </div>
      <div class="nav-wallet">0xBceFf...7b2</div>
    </nav>

    <!-- HOME TAB -->
    <div v-if="activeTab === 'home'" class="tab-content">
      <div class="hero">
        <div class="hero-badge">Powered by GenLayer AI</div>
        <h1 class="hero-title">Predict Football.<br>Earn on the Blockchain.</h1>
        <p class="hero-subtitle">GenPredict uses decentralized AI to automatically verify match results and pay out winners no middlemen, no manipulation.</p>
        <div class="hero-buttons">
          <button class="btn-primary" @click="activeTab = 'matches'; fetchMatches()">Browse Matches</button>
          <button class="btn-outline" @click="activeTab = 'predict'">My Predictions</button>
        </div>
      </div>

      <div class="features">
        <div class="feature">
          <div class="feature-icon">AI</div>
          <div class="feature-title">AI Verified Results</div>
          <div class="feature-desc">GenLayer's AI validators independently verify match results from multiple sources before paying out winners.</div>
        </div>
        <div class="feature">
          <div class="feature-icon">Fast</div>
          <div class="feature-title">Instant Predictions</div>
          <div class="feature-desc">Browse today's matches from all major leagues and place your prediction in seconds using GEN tokens.</div>
        </div>
        <div class="feature">
          <div class="feature-icon">Safe</div>
          <div class="feature-title">Fully Decentralized</div>
          <div class="feature-desc">Smart contracts handle everything from staking to payouts. No human can interfere with the results.</div>
        </div>
        <div class="feature">
          <div class="feature-icon">Global</div>
          <div class="feature-title">All Major Leagues</div>
          <div class="feature-desc">Premier League, La Liga, Serie A, Bundesliga, Champions League and hundreds more leagues covered.</div>
        </div>
      </div>

      <div class="stats">
        <div class="stat">
          <div class="stat-value">{{ matches.length }}+</div>
          <div class="stat-label">Live Matches Today</div>
        </div>
        <div class="stat">
          <div class="stat-value">5</div>
          <div class="stat-label">AI Validators</div>
        </div>
        <div class="stat">
          <div class="stat-value">100%</div>
          <div class="stat-label">Decentralized</div>
        </div>
      </div>
    </div>

    <!-- MATCHES TAB -->
    <div v-if="activeTab === 'matches'" class="tab-content">
      <div class="matches-header">
        <h2>Today's Matches</h2>
        <button class="btn-refresh" @click="fetchMatches" :disabled="loading">
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>

      <div v-if="loading" class="loading">Loading matches...</div>

      <div class="matches-grid">
        <div
          v-for="match in matches"
          :key="match.fixture.id"
          class="match-card"
          @click="selectMatch(match)"
        >
          <div class="card-league">{{ match.league.name }} · {{ match.league.country }}</div>
          <div class="card-teams">
            <div class="card-team">
              <img :src="match.teams.home.logo" class="card-logo" />
              <div class="card-name">{{ match.teams.home.name }}</div>
            </div>
            <div class="card-vs">
              <div v-if="match.fixture.status.short === 'FT'" class="card-score">
                {{ match.goals.home }} - {{ match.goals.away }}
              </div>
              <div v-else class="card-vs-text">VS</div>
              <div class="card-status" :class="match.fixture.status.short === 'FT' ? 'ft' : 'ns'">
                {{ match.fixture.status.short === 'FT' ? 'Full Time' : match.fixture.status.long }}
              </div>
            </div>
            <div class="card-team">
              <img :src="match.teams.away.logo" class="card-logo" />
              <div class="card-name">{{ match.teams.away.name }}</div>
            </div>
          </div>
          <div class="card-action">Click to predict</div>
        </div>
      </div>
    </div>

    <!-- PREDICT TAB -->
    <div v-if="activeTab === 'predict'" class="tab-content">
      <div v-if="!selectedMatch" class="empty-state">
        <div class="empty-title">No match selected</div>
        <div class="empty-desc">Go to Matches and click on a match to predict</div>
        <button class="btn-primary" @click="activeTab = 'matches'; fetchMatches()">Browse Matches</button>
      </div>

      <div v-else class="predict-detail">
        <div class="predict-league">{{ selectedMatch.league.name }} · {{ selectedMatch.fixture.date.split('T')[0] }}</div>

        <div class="predict-teams">
          <div class="predict-team">
            <img :src="selectedMatch.teams.home.logo" class="predict-logo" />
            <div class="predict-team-name">{{ selectedMatch.teams.home.name }}</div>
            <div class="predict-team-label">Home</div>
          </div>
          <div class="predict-score">
            <div v-if="selectedMatch.fixture.status.short === 'FT'">
              {{ selectedMatch.goals.home }} - {{ selectedMatch.goals.away }}
            </div>
            <div v-else>VS</div>
            <div class="predict-status" :class="selectedMatch.fixture.status.short === 'FT' ? 'ft' : 'ns'">
              {{ selectedMatch.fixture.status.long }}
            </div>
          </div>
          <div class="predict-team">
            <img :src="selectedMatch.teams.away.logo" class="predict-logo" />
            <div class="predict-team-name">{{ selectedMatch.teams.away.name }}</div>
            <div class="predict-team-label">Away</div>
          </div>
        </div>

        <div v-if="contractMatch" class="predict-contract">
          <div class="pool-title">Prediction Pool</div>
          <div class="pool-bars">
            <div class="pool-bar">
              <div class="pool-label">{{ selectedMatch.teams.home.name }} Win</div>
              <div class="pool-track">
                <div class="pool-fill home" :style="{ width: contractMatch.home_stakes + contractMatch.draw_stakes + contractMatch.away_stakes > 0 ? (contractMatch.home_stakes / (contractMatch.home_stakes + contractMatch.draw_stakes + contractMatch.away_stakes) * 100) + '%' : '33%' }"></div>
              </div>
              <div class="pool-amount">{{ contractMatch.home_stakes }} GENPRED</div>
            </div>
            <div class="pool-bar">
              <div class="pool-label">Draw</div>
              <div class="pool-track">
                <div class="pool-fill draw" :style="{ width: contractMatch.home_stakes + contractMatch.draw_stakes + contractMatch.away_stakes > 0 ? (contractMatch.draw_stakes / (contractMatch.home_stakes + contractMatch.draw_stakes + contractMatch.away_stakes) * 100) + '%' : '33%' }"></div>
              </div>
              <div class="pool-amount">{{ contractMatch.draw_stakes }} GENPRED</div>
            </div>
            <div class="pool-bar">
              <div class="pool-label">{{ selectedMatch.teams.away.name }} Win</div>
              <div class="pool-track">
                <div class="pool-fill away" :style="{ width: contractMatch.home_stakes + contractMatch.draw_stakes + contractMatch.away_stakes > 0 ? (contractMatch.away_stakes / (contractMatch.home_stakes + contractMatch.draw_stakes + contractMatch.away_stakes) * 100) + '%' : '33%' }"></div>
              </div>
              <div class="pool-amount">{{ contractMatch.away_stakes }} GENPRED</div>
            </div>
          </div>

          <div v-if="contractMatch.resolved" class="result-banner">
            Final Result: <strong>{{ contractMatch.result === 'home' ? selectedMatch.teams.home.name + ' Won' : contractMatch.result === 'away' ? selectedMatch.teams.away.name + ' Won' : 'Draw' }}</strong>
          </div>

          <div v-else class="predict-actions">
            <div class="predict-hint">Place your prediction — 100 GENPRED per stake</div>
            <div class="predict-btns">
              <button class="pbtn home" @click="stake('home')" :disabled="staking">
                {{ staking ? 'Processing...' : selectedMatch.teams.home.name + ' Wins' }}
              </button>
              <button class="pbtn draw" @click="stake('draw')" :disabled="staking">
                {{ staking ? 'Processing...' : 'Draw' }}
              </button>
              <button class="pbtn away" @click="stake('away')" :disabled="staking">
                {{ staking ? 'Processing...' : selectedMatch.teams.away.name + ' Wins' }}
              </button>
            </div>
          </div>
        </div>

        <div v-else class="not-on-chain">
          <p>This match is not on GenPredict yet. Be the first to add it!</p>
          <div class="first-predict">
            <div class="first-hint">Choose your prediction to add this match:</div>
            <div class="predict-btns">
              <button class="pbtn home" @click="createAndStake(selectedMatch, 'home')" :disabled="creating">
                {{ creating ? 'Processing...' : selectedMatch.teams.home.name + ' Wins' }}
              </button>
              <button class="pbtn draw" @click="createAndStake(selectedMatch, 'draw')" :disabled="creating">
                {{ creating ? 'Processing...' : 'Draw' }}
              </button>
              <button class="pbtn away" @click="createAndStake(selectedMatch, 'away')" :disabled="creating">
                {{ creating ? 'Processing...' : selectedMatch.teams.away.name + ' Wins' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="message" class="msg" :class="messageType">{{ message }}</div>
      </div>
    </div>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700;900&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --color-bg: #0a1a1a;
  --color-bg-accent: #0e2a2a;
  --color-primary: #ffb300;
  --color-secondary: #00e0c6;
  --color-accent: #ff3c38;
  --color-text: #f7f7f7;
  --color-muted: #7ad7c1;
  --color-card: #112222;
  --color-border: #1e4444;
}

body {
  font-family: 'Unbounded', cursive, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  min-height: 100vh;
  overflow-x: hidden;
}

.app {
  min-height: 100vh;
  position: relative;
}

/* Animated geometric background */
.app::before {
  content: '';
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  z-index: 0;
  background:
    repeating-linear-gradient(120deg, rgba(0,224,198,0.07) 0 2px, transparent 2px 80px),
    repeating-linear-gradient(-60deg, rgba(255,179,0,0.07) 0 2px, transparent 2px 80px),
    radial-gradient(circle at 70% 30%, rgba(255,60,56,0.08) 0 200px, transparent 200px 100%);
  animation: bg-move 18s linear infinite;
  pointer-events: none;
}

@keyframes bg-move {
  0% { background-position: 0 0, 0 0, 0 0; }
  100% { background-position: 120px 80px, -120px -80px, 60px 40px; }
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  height: 64px;
  background: var(--color-bg-accent);
  border-bottom: 2px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 16px 0 rgba(0,0,0,0.08);
  letter-spacing: 0.03em;
}
.nav-logo {
  font-size: 2.1rem;
  font-weight: 900;
  color: var(--color-primary);
  letter-spacing: 0.04em;
  text-shadow: 0 2px 16px rgba(255,179,0,0.12);
  font-family: 'Unbounded', cursive, sans-serif;
}
.nav-tabs { display: flex; gap: 8px; }
.nav-tab {
  padding: 10px 28px;
  background: transparent;
  color: var(--color-muted);
  border: 2px solid transparent;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  font-family: 'Unbounded', cursive, sans-serif;
}
.nav-tab:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: rgba(255,179,0,0.07);
}
.nav-tab.active {
  color: var(--color-bg);
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 2px 12px 0 rgba(255,179,0,0.13);
}
.nav-wallet {
  background: var(--color-card);
  border: 2px solid var(--color-border);
  color: var(--color-secondary);
  padding: 8px 18px;
  border-radius: 20px;
  font-size: 1rem;
  font-family: 'Unbounded', cursive, sans-serif;
  font-weight: 700;
  letter-spacing: 0.04em;
}

/* MAIN LAYOUT */
.tab-content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 48px 20px 40px;
  position: relative;
  z-index: 1;
  animation: fade-in 1.2s cubic-bezier(.77,0,.18,1) both;
}
@keyframes fade-in {
  0% { opacity: 0; transform: translateY(40px) scale(0.98); }
  100% { opacity: 1; transform: none; }
}

/* HERO SECTION */
.hero {
  text-align: center;
  padding: 80px 20px 48px;
  position: relative;
  z-index: 2;
}
.hero-badge {
  display: inline-block;
  background: var(--color-secondary);
  color: var(--color-bg);
  padding: 8px 22px;
  border-radius: 24px;
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 28px;
  letter-spacing: 0.08em;
  box-shadow: 0 2px 12px 0 rgba(0,224,198,0.13);
}
.hero-title {
  font-size: 3.2rem;
  font-weight: 900;
  line-height: 1.1;
  margin-bottom: 22px;
  color: var(--color-primary);
  text-shadow: 0 2px 24px rgba(255,179,0,0.13);
}
.hero-subtitle {
  color: var(--color-muted);
  font-size: 1.2rem;
  line-height: 1.6;
  max-width: 540px;
  margin: 0 auto 36px;
}
.hero-buttons {
  display: flex;
  gap: 18px;
  justify-content: center;
  margin-bottom: 10px;
}
.btn-primary {
  padding: 16px 38px;
  background: var(--color-primary);
  color: var(--color-bg);
  border: none;
  border-radius: 14px;
  font-size: 1.2rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 16px 0 rgba(255,179,0,0.13);
  font-family: 'Unbounded', cursive, sans-serif;
}
.btn-primary:hover {
  background: var(--color-accent);
  color: #fff;
}
.btn-outline {
  padding: 16px 38px;
  background: transparent;
  color: var(--color-secondary);
  border: 2px solid var(--color-secondary);
  border-radius: 14px;
  font-size: 1.2rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s;
  font-family: 'Unbounded', cursive, sans-serif;
}
.btn-outline:hover {
  color: var(--color-bg);
  background: var(--color-secondary);
}

/* FEATURES */
.features {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin: 70px 0 0 0;
}
.feature {
  background: var(--color-card);
  border: 2px solid var(--color-border);
  border-radius: 20px;
  padding: 32px 20px 28px 20px;
  box-shadow: 0 2px 16px 0 rgba(0,224,198,0.07);
  text-align: center;
  position: relative;
  overflow: hidden;
  animation: feature-pop 1.2s cubic-bezier(.77,0,.18,1) both;
}
@keyframes feature-pop {
  0% { opacity: 0; transform: scale(0.8) translateY(40px); }
  100% { opacity: 1; transform: none; }
}
.feature-icon {
  display: inline-block;
  background: var(--color-secondary);
  color: var(--color-bg);
  padding: 7px 18px;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: 900;
  letter-spacing: 0.09em;
  margin-bottom: 18px;
  box-shadow: 0 2px 12px 0 rgba(0,224,198,0.13);
}
.feature-title {
  font-size: 1.2rem;
  font-weight: 800;
  margin-bottom: 10px;
  color: var(--color-primary);
}
.feature-desc {
  color: var(--color-muted);
  font-size: 1rem;
  line-height: 1.7;
}

/* STATS */
.stats {
  display: flex;
  gap: 2px;
  background: var(--color-border);
  border-radius: 20px;
  overflow: hidden;
  margin-top: 48px;
}
.stat {
  flex: 1;
  padding: 38px 0;
  text-align: center;
  background: var(--color-card);
}
.stat-value {
  font-size: 2.3rem;
  font-weight: 900;
  color: var(--color-secondary);
  margin-bottom: 6px;
  text-shadow: 0 2px 12px rgba(0,224,198,0.13);
}
.stat-label {
  color: var(--color-muted);
  font-size: 1.1rem;
}


.nav-logo { font-size: 1.2rem; font-weight: 800; color: #fff; }

.nav-tabs { display: flex; gap: 4px; }

.nav-tab {
  padding: 8px 20px;
  background: transparent;
  color: #555;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-tab:hover { color: #888; background: #1a1a1a; }
.nav-tab.active { color: #fff; background: #1a1a1a; }

.nav-wallet {
  background: #1a1a1a;
  border: 1px solid #222;
  color: #666;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
}

.tab-content { max-width: 1100px; margin: 0 auto; padding: 40px 20px; }

.hero { text-align: center; padding: 60px 20px 40px; }

.hero-badge {
  display: inline-block;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  color: #818cf8;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 24px;
}

.hero-title { font-size: 3rem; font-weight: 800; line-height: 1.1; margin-bottom: 20px; color: #fff; }
.hero-subtitle { color: #555; font-size: 1.1rem; line-height: 1.6; max-width: 500px; margin: 0 auto 32px; }
.hero-buttons { display: flex; gap: 12px; justify-content: center; }

.btn-primary { padding: 14px 32px; background: #4f46e5; color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-primary:hover { background: #4338ca; }

.btn-outline { padding: 14px 32px; background: transparent; color: #555; border: 1px solid #222; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-outline:hover { color: #888; border-color: #333; }

.features { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 60px 0; }

.feature { background: #111; border: 1px solid #1a1a1a; border-radius: 16px; padding: 24px; }

.feature-icon {
  display: inline-block;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.2);
  color: #818cf8;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 14px;
}

.feature-title { font-size: 15px; font-weight: 700; margin-bottom: 8px; color: #fff; }
.feature-desc { color: #555; font-size: 13px; line-height: 1.6; }

.stats { display: flex; gap: 1px; background: #1a1a1a; border-radius: 16px; overflow: hidden; }
.stat { flex: 1; padding: 32px; text-align: center; background: #111; }
.stat-value { font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 4px; }
.stat-label { color: #555; font-size: 13px; }

.matches-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.matches-header h2 { font-size: 1.4rem; font-weight: 700; }
.btn-refresh { padding: 8px 20px; background: #1a1a1a; color: #555; border: 1px solid #222; border-radius: 8px; font-size: 13px; cursor: pointer; }
.loading { color: #444; text-align: center; padding: 40px; }

.matches-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }

.match-card { background: #111; border: 1px solid #1a1a1a; border-radius: 16px; padding: 20px; cursor: pointer; transition: all 0.2s; }
.match-card:hover { border-color: #333; background: #151515; }

.card-league { color: #444; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }
.card-teams { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.card-team { text-align: center; flex: 1; }
.card-logo { width: 36px; height: 36px; object-fit: contain; margin-bottom: 6px; }
.card-name { font-size: 12px; font-weight: 600; color: #ccc; }
.card-vs { text-align: center; }
.card-score { font-size: 1.2rem; font-weight: 800; color: #fff; }
.card-vs-text { font-size: 13px; color: #333; font-weight: 700; }
.card-status { font-size: 10px; margin-top: 4px; }
.card-status.ft { color: #22c55e; }
.card-status.ns { color: #f59e0b; }
.card-action { text-align: center; color: #333; font-size: 11px; }

.empty-state { text-align: center; padding: 100px 20px; }
.empty-title { font-size: 1.2rem; font-weight: 700; margin-bottom: 8px; }
.empty-desc { color: #555; margin-bottom: 24px; }

.predict-league { color: #555; font-size: 13px; margin-bottom: 32px; }

.predict-teams { display: flex; align-items: center; justify-content: space-between; margin-bottom: 40px; background: #111; border: 1px solid #1a1a1a; border-radius: 20px; padding: 32px; }

.predict-team { text-align: center; flex: 1; }
.predict-logo { width: 72px; height: 72px; object-fit: contain; margin-bottom: 12px; }
.predict-team-name { font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; }
.predict-team-label { color: #555; font-size: 12px; }
.predict-score { text-align: center; font-size: 2rem; font-weight: 800; padding: 0 20px; }
.predict-status { font-size: 12px; margin-top: 8px; }
.predict-status.ft { color: #22c55e; }
.predict-status.ns { color: #f59e0b; }

.predict-contract { background: #111; border: 1px solid #1a1a1a; border-radius: 20px; padding: 32px; }

.pool-title { font-size: 13px; color: #555; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }

.pool-bars { display: flex; flex-direction: column; gap: 14px; margin-bottom: 28px; }
.pool-bar { display: flex; align-items: center; gap: 12px; }
.pool-label { color: #666; font-size: 13px; width: 140px; flex-shrink: 0; }
.pool-track { flex: 1; height: 6px; background: #1a1a1a; border-radius: 3px; overflow: hidden; }
.pool-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.pool-fill.home { background: #22c55e; }
.pool-fill.draw { background: #f59e0b; }
.pool-fill.away { background: #ef4444; }
.pool-amount { color: #666; font-size: 13px; width: 80px; text-align: right; }

.result-banner { text-align: center; padding: 20px; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.2); border-radius: 12px; color: #22c55e; font-size: 1.1rem; }

.predict-hint { color: #555; font-size: 13px; margin-bottom: 12px; }
.predict-btns { display: flex; gap: 12px; }

.pbtn { flex: 1; padding: 16px; border-radius: 12px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; border: 1px solid; }
.pbtn:disabled { opacity: 0.4; cursor: not-allowed; }
.pbtn.home { background: rgba(34,197,94,0.1); color: #22c55e; border-color: rgba(34,197,94,0.2); }
.pbtn.home:hover:not(:disabled) { background: rgba(34,197,94,0.2); }
.pbtn.draw { background: rgba(245,158,11,0.1); color: #f59e0b; border-color: rgba(245,158,11,0.2); }
.pbtn.draw:hover:not(:disabled) { background: rgba(245,158,11,0.2); }
.pbtn.away { background: rgba(239,68,68,0.1); color: #ef4444; border-color: rgba(239,68,68,0.2); }
.pbtn.away:hover:not(:disabled) { background: rgba(239,68,68,0.2); }

.not-on-chain { background: #111; border: 1px solid #1a1a1a; border-radius: 20px; padding: 32px; text-align: center; }
.not-on-chain p { color: #555; margin-bottom: 24px; }
.first-hint { color: #555; font-size: 13px; margin-bottom: 12px; }

.msg { margin-top: 16px; padding: 12px 16px; border-radius: 10px; font-size: 13px; }
.msg.info { background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); }
.msg.success { background: rgba(34,197,94,0.1); color: #22c55e; border: 1px solid rgba(34,197,94,0.2); }
.msg.error { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.2); }
</style>