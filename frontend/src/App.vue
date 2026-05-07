<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

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
const walletAddress = ref('')
const balance = ref(0)
const stakeAmount = ref(1000)
const apiNotice = ref('')
const feedMode = ref<'api' | 'demo'>('api')
const showWalletPicker = ref(false)
const availableWallets = ref<any[]>([])
const predictions = ref<any[]>([])
const pendingPrediction = ref<any>(null)
const matchSearch = ref('')
const sourceFilter = ref('all')
const statusFilter = ref('all')
const STORAGE_KEYS = {
  wallet: 'genpredict.wallet',
  balance: 'genpredict.balance',
  claimed: 'genpredict.claimed',
  predictions: 'genpredict.predictions'
}
const normalizedStake = computed(() => Math.max(100, Number(stakeAmount.value) || 100))
const homeStake = computed(() => Number(contractMatch.value?.home_stakes) || 0)
const drawStake = computed(() => Number(contractMatch.value?.draw_stakes) || 0)
const awayStake = computed(() => Number(contractMatch.value?.away_stakes) || 0)
const totalPool = computed(() => homeStake.value + drawStake.value + awayStake.value)
const homeOdds = computed(() => contractMatch.value ? parseFloat(((drawStake.value + awayStake.value + normalizedStake.value) / Math.max(homeStake.value + normalizedStake.value, 1)).toFixed(2)) : 2.0)
const drawOdds = computed(() => contractMatch.value ? parseFloat(((homeStake.value + awayStake.value + normalizedStake.value) / Math.max(drawStake.value + normalizedStake.value, 1)).toFixed(2)) : 3.0)
const awayOdds = computed(() => contractMatch.value ? parseFloat(((homeStake.value + drawStake.value + normalizedStake.value) / Math.max(awayStake.value + normalizedStake.value, 1)).toFixed(2)) : 2.5)
const matchFeedTitle = computed(() => feedMode.value === 'demo' ? 'Demo Matches' : 'Upcoming Matches')
const sortedPredictions = computed(() =>
  [...predictions.value].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
)
const filteredMatches = computed(() => {
  const query = matchSearch.value.trim().toLowerCase()

  return matches.value.filter((match: any) => {
    const isDemo = String(match.fixture.id).startsWith('demo_')
    const status = match.fixture.status.short
    const text = `${match.teams.home.name} ${match.teams.away.name} ${match.league.name} ${match.league.country}`.toLowerCase()

    if (sourceFilter.value === 'real' && isDemo) return false
    if (sourceFilter.value === 'demo' && !isDemo) return false
    if (statusFilter.value === 'live' && !['1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP', 'INT', 'LIVE'].includes(status)) return false
    if (statusFilter.value === 'upcoming' && status !== 'NS' && status !== 'TBD') return false

    return !query || text.includes(query)
  })
})
const leaderboard = computed(() => {
  const table = new Map<string, any>()

  for (const prediction of predictions.value) {
    const key = walletAddress.value || 'Demo user'
    const current = table.get(key) || {
      wallet: key,
      predictions: 0,
      totalStaked: 0,
      potentialPayout: 0
    }

    current.predictions += 1
    current.totalStaked += Number(prediction.amount) || 0
    current.potentialPayout += Number(prediction.potentialPayout) || 0
    table.set(key, current)
  }

  return [...table.values()].sort((a, b) => b.potentialPayout - a.potentialPayout)
})
const verificationItems = computed(() => [
  { label: 'Result oracle', value: 'AI validation pending' },
  { label: 'Payout state', value: sortedPredictions.value.length ? 'Awaiting final scores' : 'No active predictions' },
  { label: 'Source check', value: feedMode.value === 'demo' ? 'Demo feed' : 'Football API feed' }
])
const closedStatuses = new Set(['FT', 'AET', 'PEN', 'CANC', 'PST', 'ABD', 'AWD', 'WO'])
const validTabs = new Set(['home', 'matches', 'predict', 'predictions'])

function getTabFromLocation() {
  const tab = window.location.hash.replace('#', '')
  return validTabs.has(tab) ? tab : 'home'
}

function navigate(tab: string, replace = false) {
  activeTab.value = tab

  if (tab === 'matches') fetchMatches()

  const nextUrl = `${window.location.pathname}${window.location.search}#${tab}`
  if (window.location.hash !== `#${tab}`) {
    const method = replace ? 'replaceState' : 'pushState'
    window.history[method]({ tab }, '', nextUrl)
  }
}

function getPredictionLabel(match: any, prediction: string) {
  if (prediction === 'home') return `${match.teams.home.name} win`
  if (prediction === 'away') return `${match.teams.away.name} win`
  return 'Draw'
}

function getPredictionOdds(prediction: string) {
  if (prediction === 'home') return homeOdds.value
  if (prediction === 'away') return awayOdds.value
  return drawOdds.value
}

function syncTabFromHistory() {
  activeTab.value = getTabFromLocation()
  if (activeTab.value === 'matches') fetchMatches()
}

function formatLocalMatchDate(date: Date) {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })

  return formatter.format(date)
}

function getUpcomingDates(days = 7) {
  return Array.from({ length: days }, (_, index) => {
    const date = new Date()
    date.setDate(date.getDate() + index)
    return formatLocalMatchDate(date)
  })
}

function hasApiErrors(errors: unknown) {
  return !!errors && typeof errors === 'object' && Object.keys(errors).length > 0
}

function getApiErrorMessage(errors: any) {
  if (!hasApiErrors(errors)) return ''
  return Object.values(errors).join(' ')
}

function getInjectedWallets() {
  const ethereum = (window as any).ethereum
  if (!ethereum) return []

  const providers = Array.isArray(ethereum.providers) ? ethereum.providers : [ethereum]
  const named = providers.map((provider: any) => {
    const name =
      provider.isMetaMask ? 'MetaMask' :
      provider.isCoinbaseWallet ? 'Coinbase Wallet' :
      provider.isRabby ? 'Rabby' :
      provider.isTrust ? 'Trust Wallet' :
      provider.isBraveWallet ? 'Brave Wallet' :
      'Browser Wallet'

    return { name, provider }
  })

  return named.filter((wallet: any, index: number, list: any[]) =>
    list.findIndex((item: any) => item.name === wallet.name) === index
  )
}

function showDemoMatches() {
  feedMode.value = 'demo'
  apiNotice.value = 'Showing demo matches while live fixtures refresh.'
  matches.value = createDemoMatches()
}

function showRealMatches() {
  feedMode.value = 'api'
  fetchMatches()
}

function isDemoMatch(match: any) {
  return String(match.fixture.id).startsWith('demo_')
}

async function fetchFixturesByDate(date: string, timezone: string) {
  const params = new URLSearchParams({ date, timezone })
  const proxyRes = await fetch(`/api/fixtures?${params.toString()}`)

  if (proxyRes.ok) return proxyRes.json()

  const directRes = await fetch(
    `https://v3.football.api-sports.io/fixtures?date=${date}&timezone=${encodeURIComponent(timezone)}`,
    { headers: { 'x-apisports-key': API_KEY } }
  )

  if (!directRes.ok) throw new Error(`Football API request failed with ${directRes.status}`)
  return directRes.json()
}

function createDemoMatches() {
  const teams = [
    ['Arsenal', 'Chelsea'],
    ['Barcelona', 'Sevilla'],
    ['Inter', 'Napoli'],
    ['Borussia Dortmund', 'RB Leipzig'],
    ['Paris Saint-Germain', 'Marseille'],
    ['Ajax', 'PSV Eindhoven']
  ]

  return teams.map(([home, away], index) => {
    const kickoff = new Date()
    kickoff.setHours(kickoff.getHours() + 2 + index * 3, 0, 0, 0)

    return {
      fixture: {
        id: `demo_${index + 1}`,
        date: kickoff.toISOString(),
        status: { short: 'NS', long: 'Not Started' }
      },
      league: {
        name: 'Demo League',
        country: 'GenPredict'
      },
      teams: {
        home: {
          name: home,
          logo: `https://ui-avatars.com/api/?name=${encodeURIComponent(home)}&background=147d64&color=fff&bold=true`
        },
        away: {
          name: away,
          logo: `https://ui-avatars.com/api/?name=${encodeURIComponent(away)}&background=e1a72f&color=14211b&bold=true`
        }
      },
      goals: { home: null, away: null }
    }
  })
}

async function connectWallet() {
  availableWallets.value = getInjectedWallets()

  if (!availableWallets.value.length) {
    message.value = 'No browser wallet found. Install MetaMask, Coinbase Wallet, Rabby, or another EVM wallet.'
    messageType.value = 'error'
    return
  }

  if (availableWallets.value.length > 1) {
    showWalletPicker.value = true
    return
  }

  await connectWalletProvider(availableWallets.value[0].provider)
}

async function connectWalletProvider(provider: any) {
  try {
    const accounts = await provider.request({ method: 'eth_requestAccounts' })
    walletAddress.value = accounts[0]
    localStorage.setItem(STORAGE_KEYS.wallet, accounts[0])
    showWalletPicker.value = false
  } catch (e) {
    console.error(e)
    message.value = 'Wallet connection failed.'
    messageType.value = 'error'
  }
}

const claimed = ref(false)
function claimTokens() {
  if (claimed.value) return
  balance.value = 100000
  claimed.value = true
  localStorage.setItem(STORAGE_KEYS.balance, String(balance.value))
  localStorage.setItem(STORAGE_KEYS.claimed, 'true')
  message.value = '100,000 GENPRED claimed!'
  messageType.value = 'success'
}

function disconnectWallet() {
  walletAddress.value = ''
  localStorage.removeItem(STORAGE_KEYS.wallet)
  message.value = 'Wallet disconnected.'
  messageType.value = 'info'
}

function persistBalance() {
  localStorage.setItem(STORAGE_KEYS.balance, String(balance.value))
}

function persistPredictions() {
  localStorage.setItem(STORAGE_KEYS.predictions, JSON.stringify(predictions.value))
}

function restoreSession() {
  walletAddress.value = localStorage.getItem(STORAGE_KEYS.wallet) || ''
  balance.value = Number(localStorage.getItem(STORAGE_KEYS.balance)) || 0
  claimed.value = localStorage.getItem(STORAGE_KEYS.claimed) === 'true'
  try {
    predictions.value = JSON.parse(localStorage.getItem(STORAGE_KEYS.predictions) || '[]')
  } catch {
    predictions.value = []
  }
}

function handleAccountsChanged(accounts: string[]) {
  if (!accounts.length) {
    disconnectWallet()
    return
  }

  walletAddress.value = accounts[0]
  localStorage.setItem(STORAGE_KEYS.wallet, accounts[0])
}

async function getClient() {
  const { createClient, createAccount } = await import('genlayer-js')
  const { studionet } = await import('genlayer-js/chains')
  return createClient({ chain: studionet, account: createAccount() })
}

async function fetchMatches() {
  loading.value = true
  apiNotice.value = ''
  feedMode.value = 'api'
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    const upcomingMatches = []

    for (const date of getUpcomingDates(2)) {
      const data = await fetchFixturesByDate(date, timezone)
      if (hasApiErrors(data.errors)) throw new Error(getApiErrorMessage(data.errors))
      if (!Array.isArray(data.response)) throw new Error(data.message || 'Football API returned no matches')

      upcomingMatches.push(
        ...data.response.filter((match: any) => !closedStatuses.has(match.fixture.status.short))
      )
      if (upcomingMatches.length >= 30) break
    }

    matches.value = upcomingMatches
      .sort((a: any, b: any) => new Date(a.fixture.date).getTime() - new Date(b.fixture.date).getTime())
      .slice(0, 30)

    if (!matches.value.length) {
      showDemoMatches()
    }
  } catch (e) {
    console.error(e)
    showDemoMatches()
  } finally {
    loading.value = false
  }
}

async function selectMatch(match: any, pushHistory = true) {
  selectedMatch.value = match
  contractMatch.value = null
  navigate('predict', !pushHistory)
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

function openPredictionConfirm(mode: 'create' | 'stake', match: any, prediction: string) {
  if (closedStatuses.has(match.fixture.status.short)) {
    message.value = 'This match is already closed for predictions.'
    messageType.value = 'error'
    return
  }
  if (!walletAddress.value) {
    message.value = 'Connect a wallet before placing a prediction.'
    messageType.value = 'error'
    return
  }
  if (balance.value < normalizedStake.value) {
    message.value = 'Claim tokens or lower your stake amount first.'
    messageType.value = 'error'
    return
  }

  pendingPrediction.value = {
    mode,
    match,
    prediction,
    label: getPredictionLabel(match, prediction),
    amount: normalizedStake.value,
    odds: getPredictionOdds(prediction)
  }
}

function cancelPredictionConfirm() {
  pendingPrediction.value = null
}

async function confirmPrediction() {
  if (!pendingPrediction.value) return
  const pending = pendingPrediction.value
  pendingPrediction.value = null

  if (pending.mode === 'create') {
    await createAndStake(pending.match, pending.prediction, pending)
    return
  }

  await stake(pending.prediction, pending)
}

function recordPrediction(match: any, prediction: string, amount: number, odds: number, createdPool: boolean) {
  predictions.value.unshift({
    id: `${match.fixture.id}_${Date.now()}`,
    matchId: `match_${match.fixture.id}`,
    homeTeam: match.teams.home.name,
    awayTeam: match.teams.away.name,
    league: match.league.name,
    date: match.fixture.date,
    prediction,
    predictionLabel: getPredictionLabel(match, prediction),
    amount,
    odds,
    potentialPayout: Math.round(amount * odds),
    status: 'Pending',
    createdPool,
    createdAt: new Date().toISOString()
  })
  persistPredictions()
}

async function createAndStake(match: any, prediction: string, pending = { amount: normalizedStake.value, odds: getPredictionOdds(prediction) }) {
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
      args: [matchId, prediction, pending.amount, walletAddress.value],
      value: 0n,
      leaderOnly: true
    } as any)

    balance.value = Math.max(0, balance.value - pending.amount)
    persistBalance()
    recordPrediction(match, prediction, pending.amount, pending.odds, true)
    message.value = 'Stake placed successfully!'
    messageType.value = 'success'
    await selectMatch(match, false)
  } catch (e) {
    console.error(e)
    message.value = 'Something went wrong. Try again.'
    messageType.value = 'error'
  }
  creating.value = false
  staking.value = false
}

async function stake(prediction: string, pending = { amount: normalizedStake.value, odds: getPredictionOdds(prediction) }) {
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
      args: [matchId, prediction, pending.amount, walletAddress.value],
      value: 0n,
      leaderOnly: true
    } as any)

    balance.value = Math.max(0, balance.value - pending.amount)
    persistBalance()
    recordPrediction(selectedMatch.value, prediction, pending.amount, pending.odds, false)
    message.value = 'Stake placed successfully!'
    messageType.value = 'success'
    await selectMatch(selectedMatch.value, false)
  } catch (e) {
    console.error(e)
    message.value = 'Stake failed. Try again.'
    messageType.value = 'error'
  }
  staking.value = false
}

onMounted(() => {
  restoreSession()
  syncTabFromHistory()
  fetchMatches()
  window.addEventListener('popstate', syncTabFromHistory)
  ;(window as any).ethereum?.on?.('accountsChanged', handleAccountsChanged)
})

onUnmounted(() => {
  window.removeEventListener('popstate', syncTabFromHistory)
  ;(window as any).ethereum?.removeListener?.('accountsChanged', handleAccountsChanged)
})
</script>

<template>
  <div class="app">
    <nav class="navbar">
      <div class="nav-logo">GenPredict</div>
      <div class="nav-tabs">
        <button :class="['nav-tab', activeTab === 'home' ? 'active' : '']" @click="navigate('home')">Home</button>
        <button :class="['nav-tab', activeTab === 'matches' ? 'active' : '']" @click="navigate('matches')">Matches</button>
        <button :class="['nav-tab', activeTab === 'predictions' ? 'active' : '']" @click="navigate('predictions')">My Predictions</button>
      </div>
      <div class="nav-right">
        <button v-if="!walletAddress && !showWalletPicker" class="btn-connect" @click="connectWallet">Connect Wallet</button>
        <div v-else-if="showWalletPicker" class="wallet-picker">
          <button
            v-for="wallet in availableWallets"
            :key="wallet.name"
            class="wallet-option"
            @click="connectWalletProvider(wallet.provider)"
          >
            {{ wallet.name }}
          </button>
          <button class="wallet-option muted" @click="showWalletPicker = false">Cancel</button>
        </div>
        <div v-else class="wallet-group">
          <div class="nav-wallet">{{ walletAddress.slice(0,6) }}...{{ walletAddress.slice(-4) }}</div>
          <button class="btn-disconnect" @click="disconnectWallet">Disconnect</button>
        </div>
        <button v-if="!claimed" class="btn-claim" @click="claimTokens">Claim Demo GENPRED</button>
        <div v-else class="nav-balance">Demo: {{ balance.toLocaleString() }} GENPRED</div>
      </div>
    </nav>

    <!-- HOME TAB -->
    <div v-if="activeTab === 'home'" class="tab-content">
      <div class="hero">
        <div class="hero-badge">Powered by GenLayer AI</div>
        <h1 class="hero-title">Predict Football.<br>Earn on the Blockchain.</h1>
        <p class="hero-subtitle">GenPredict uses decentralized AI to automatically verify match results and pay out winners no middlemen, no manipulation.</p>
        <div class="hero-buttons">
          <button class="btn-primary" @click="navigate('matches')">Browse Matches</button>
          <button class="btn-outline" @click="navigate('predictions')">My Predictions</button>
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
        <h2>{{ matchFeedTitle }}</h2>
        <button class="btn-refresh" @click="fetchMatches" :disabled="loading">
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>

      <div v-if="apiNotice" class="api-notice">
        {{ apiNotice }}
      </div>

      <div class="feed-note">
        Real fixtures appear automatically when available. Demo matches keep predictions testable while the feed refreshes.
      </div>

      <div class="feed-legend">
        <span><strong>Real</strong> live fixture data from the football feed</span>
        <span><strong>Demo</strong> sample matches for testing predictions</span>
      </div>

      <div class="match-tools">
        <input v-model="matchSearch" class="match-search" placeholder="Search team or league" />
        <select v-model="sourceFilter" class="match-select">
          <option value="all">All sources</option>
          <option value="real">Real only</option>
          <option value="demo">Demo only</option>
        </select>
        <select v-model="statusFilter" class="match-select">
          <option value="all">All statuses</option>
          <option value="upcoming">Upcoming</option>
          <option value="live">Live</option>
        </select>
        <button class="btn-refresh" @click="showDemoMatches">Demo mode</button>
        <button class="btn-refresh" @click="showRealMatches">Real feed</button>
      </div>

      <div v-if="loading" class="loading">Loading matches...</div>

      <div v-else-if="!filteredMatches.length" class="empty-state compact">
        <div class="empty-title">No upcoming matches found</div>
        <div class="empty-desc">Try changing filters, switching to demo mode, or refreshing the live feed.</div>
        <button class="btn-primary" @click="fetchMatches">Refresh matches</button>
      </div>

      <div class="matches-grid">
        <div
          v-for="match in filteredMatches"
          :key="match.fixture.id"
          class="match-card"
          @click="selectMatch(match)"
        >
          <div class="card-topline">
            <div class="card-league">{{ match.league.name }} · {{ match.league.country }}</div>
            <div :class="['feed-badge', isDemoMatch(match) ? 'demo' : 'real']">
              {{ isDemoMatch(match) ? 'Demo' : 'Real' }}
            </div>
          </div>
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
          <div class="card-action">{{ feedMode === 'demo' ? 'Demo prediction' : 'Click to predict' }}</div>
        </div>
      </div>
    </div>

    <!-- PREDICT TAB -->
    <div v-if="activeTab === 'predict'" class="tab-content">
      <div v-if="!selectedMatch" class="empty-state">
        <div class="empty-title">No match selected</div>
        <div class="empty-desc">Go to Matches and click on a match to predict</div>
        <button class="btn-primary" @click="navigate('matches')">Browse Matches</button>
      </div>

      <div v-else class="predict-detail">
        <button class="back-link" @click="navigate('matches')">Back to matches</button>
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
                <div class="pool-fill home" :style="{ width: totalPool > 0 ? (homeStake / totalPool * 100) + '%' : '33%' }"></div>
              </div>
              <div class="pool-amount">{{ homeStake.toLocaleString() }} GENPRED</div>
            </div>
            <div class="pool-bar">
              <div class="pool-label">Draw</div>
              <div class="pool-track">
                <div class="pool-fill draw" :style="{ width: totalPool > 0 ? (drawStake / totalPool * 100) + '%' : '33%' }"></div>
              </div>
              <div class="pool-amount">{{ drawStake.toLocaleString() }} GENPRED</div>
            </div>
            <div class="pool-bar">
              <div class="pool-label">{{ selectedMatch.teams.away.name }} Win</div>
              <div class="pool-track">
                <div class="pool-fill away" :style="{ width: totalPool > 0 ? (awayStake / totalPool * 100) + '%' : '33%' }"></div>
              </div>
              <div class="pool-amount">{{ awayStake.toLocaleString() }} GENPRED</div>
            </div>
          </div>

          <div v-if="contractMatch.resolved" class="result-banner">
            Final Result: <strong>{{ contractMatch.result === 'home' ? selectedMatch.teams.home.name + ' Won' : contractMatch.result === 'away' ? selectedMatch.teams.away.name + ' Won' : 'Draw' }}</strong>
          </div>

          <div v-else class="predict-actions">
            <div class="predict-hint">Demo balance: {{ balance.toLocaleString() }} GENPRED</div>
<div class="stake-input-row">
  <label>Stake amount:</label>
  <input type="number" v-model.number="stakeAmount" min="100" step="100" class="stake-input" />
  <span class="stake-currency">GENPRED</span>
</div>
<div class="odds-row">
  <div class="odd-box">Home Win odds: <strong>{{ homeOdds }}x</strong> · Win: <strong>{{ (normalizedStake * homeOdds).toLocaleString() }} GENPRED</strong></div>
  <div class="odd-box">Draw odds: <strong>{{ drawOdds }}x</strong> · Win: <strong>{{ (normalizedStake * drawOdds).toLocaleString() }} GENPRED</strong></div>
  <div class="odd-box">Away Win odds: <strong>{{ awayOdds }}x</strong> · Win: <strong>{{ (normalizedStake * awayOdds).toLocaleString() }} GENPRED</strong></div>
</div>
            <div class="predict-btns">
              <button class="pbtn home" @click="openPredictionConfirm('stake', selectedMatch, 'home')" :disabled="staking">
                {{ staking ? 'Processing...' : selectedMatch.teams.home.name + ' Wins' }}
              </button>
              <button class="pbtn draw" @click="openPredictionConfirm('stake', selectedMatch, 'draw')" :disabled="staking">
                {{ staking ? 'Processing...' : 'Draw' }}
              </button>
              <button class="pbtn away" @click="openPredictionConfirm('stake', selectedMatch, 'away')" :disabled="staking">
                {{ staking ? 'Processing...' : selectedMatch.teams.away.name + ' Wins' }}
              </button>
            </div>
          </div>
        </div>

        <div v-else class="not-on-chain">
          <p>No prediction pool exists for this match yet. Create the pool and place your first stake in one step.</p>
          <div class="first-predict">
            <div class="first-hint">Demo balance: {{ balance.toLocaleString() }} GENPRED</div>
            <div class="stake-input-row">
              <label>Stake amount:</label>
              <input type="number" v-model.number="stakeAmount" min="100" step="100" class="stake-input" />
              <span class="stake-currency">GENPRED</span>
            </div>
            <div class="odds-row">
              <div class="odd-box">Home estimate: <strong>{{ homeOdds }}x</strong> · Win: <strong>{{ (normalizedStake * homeOdds).toLocaleString() }} GENPRED</strong></div>
              <div class="odd-box">Draw estimate: <strong>{{ drawOdds }}x</strong> · Win: <strong>{{ (normalizedStake * drawOdds).toLocaleString() }} GENPRED</strong></div>
              <div class="odd-box">Away estimate: <strong>{{ awayOdds }}x</strong> · Win: <strong>{{ (normalizedStake * awayOdds).toLocaleString() }} GENPRED</strong></div>
            </div>
            <div class="predict-btns">
              <button class="pbtn home" @click="openPredictionConfirm('create', selectedMatch, 'home')" :disabled="creating">
                {{ creating ? 'Processing...' : 'Create pool · ' + selectedMatch.teams.home.name }}
              </button>
              <button class="pbtn draw" @click="openPredictionConfirm('create', selectedMatch, 'draw')" :disabled="creating">
                {{ creating ? 'Processing...' : 'Create pool · Draw' }}
              </button>
              <button class="pbtn away" @click="openPredictionConfirm('create', selectedMatch, 'away')" :disabled="creating">
                {{ creating ? 'Processing...' : 'Create pool · ' + selectedMatch.teams.away.name }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="message" class="msg" :class="messageType">{{ message }}</div>
      </div>
    </div>

    <!-- MY PREDICTIONS TAB -->
    <div v-if="activeTab === 'predictions'" class="tab-content">
      <div class="matches-header">
        <h2>My Predictions</h2>
        <button class="btn-refresh" @click="navigate('matches')">Find matches</button>
      </div>

      <div v-if="!sortedPredictions.length" class="empty-state compact">
        <div class="empty-title">No predictions yet</div>
        <div class="empty-desc">Choose a match, confirm your stake, and your predictions will appear here.</div>
        <button class="btn-primary" @click="navigate('matches')">Browse matches</button>
      </div>

      <div v-else class="prediction-list">
        <div v-for="prediction in sortedPredictions" :key="prediction.id" class="prediction-card">
          <div>
            <div class="prediction-league">{{ prediction.league }} · {{ prediction.status }}</div>
            <div class="prediction-title">{{ prediction.homeTeam }} vs {{ prediction.awayTeam }}</div>
            <div class="prediction-choice">{{ prediction.predictionLabel }}</div>
          </div>
          <div class="prediction-metrics">
            <div>
              <span>Stake</span>
              <strong>{{ prediction.amount.toLocaleString() }} GENPRED</strong>
            </div>
            <div>
              <span>Odds</span>
              <strong>{{ prediction.odds }}x</strong>
            </div>
            <div>
              <span>Potential</span>
              <strong>{{ prediction.potentialPayout.toLocaleString() }} GENPRED</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="insight-grid">
        <section class="insight-panel">
          <div class="panel-title">Leaderboard</div>
          <div v-if="!leaderboard.length" class="panel-empty">Place a prediction to enter the table.</div>
          <div v-for="entry in leaderboard" :key="entry.wallet" class="leader-row">
            <div>
              <strong>{{ entry.wallet.slice(0, 6) }}{{ entry.wallet.length > 10 ? '...' + entry.wallet.slice(-4) : '' }}</strong>
              <span>{{ entry.predictions }} predictions</span>
            </div>
            <div>{{ entry.potentialPayout.toLocaleString() }} GENPRED</div>
          </div>
        </section>

        <section class="insight-panel">
          <div class="panel-title">Result Verification</div>
          <div v-for="item in verificationItems" :key="item.label" class="verify-row">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </section>
      </div>
    </div>

    <div v-if="pendingPrediction" class="modal-backdrop">
      <div class="confirm-modal">
        <div class="modal-kicker">Confirm prediction</div>
        <h2>{{ pendingPrediction.label }}</h2>
        <p>
          You are staking <strong>{{ pendingPrediction.amount.toLocaleString() }} GENPRED</strong>
          on {{ pendingPrediction.match.teams.home.name }} vs {{ pendingPrediction.match.teams.away.name }}.
        </p>
        <div class="confirm-grid">
          <div>
            <span>Odds</span>
            <strong>{{ pendingPrediction.odds }}x</strong>
          </div>
          <div>
            <span>Potential return</span>
            <strong>{{ (pendingPrediction.amount * pendingPrediction.odds).toLocaleString() }} GENPRED</strong>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-outline" @click="cancelPredictionConfirm">Cancel</button>
          <button class="btn-primary" @click="confirmPrediction" :disabled="staking || creating">
            {{ staking || creating ? 'Processing...' : 'Confirm stake' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

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
.empty-state.compact { padding: 34px 20px; }
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
.nav-right { display: flex; align-items: center; gap: 12px; }
.btn-connect { padding: 8px 20px; background: #4f46e5; color: #fff; border: none; border-radius: 20px; font-size: 13px; font-weight: 600; cursor: pointer; }
.nav-balance { background: #1a1a1a; border: 1px solid #222; color: #22c55e; padding: 6px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; }
.btn-claim { padding: 8px 20px; background: #22c55e; color: #000; border: none; border-radius: 20px; font-size: 13px; font-weight: 700; cursor: pointer; }
.stake-input-row { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.stake-input { background: #1a1a1a; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 8px; font-size: 14px; width: 150px; }
.stake-currency { color: #555; font-size: 13px; }
.odds-row { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.odd-box { background: #1a1a1a; border: 1px solid #222; padding: 10px 16px; border-radius: 8px; font-size: 13px; color: #888; }
.odd-box strong { color: #22c55e; }

:root {
  --page: #f3f6f1;
  --surface: #ffffff;
  --surface-soft: #e9efe6;
  --surface-strong: #10382b;
  --ink: #14211b;
  --muted: #65736c;
  --line: #d7e0d6;
  --primary: #147d64;
  --primary-dark: #0c5f4b;
  --accent: #e1a72f;
  --danger: #c24138;
  --success: #248a4d;
  --shadow: 0 18px 48px rgba(34, 55, 43, 0.11);
}

body {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background:
    linear-gradient(135deg, rgba(20, 125, 100, 0.08), transparent 36%),
    linear-gradient(315deg, rgba(225, 167, 47, 0.16), transparent 32%),
    var(--page);
  color: var(--ink);
}

.app {
  background: transparent;
  color: var(--ink);
}

.app::before {
  display: none;
}

.navbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 24px;
  align-items: center;
  height: auto;
  min-height: 76px;
  padding: 14px clamp(18px, 4vw, 56px);
  background: rgba(255, 255, 255, 0.86);
  border: 0;
  border-bottom: 1px solid rgba(16, 56, 43, 0.12);
  border-radius: 0;
  box-shadow: 0 10px 32px rgba(20, 33, 27, 0.08);
  backdrop-filter: blur(18px);
  animation: none;
  letter-spacing: 0;
}

.nav-logo {
  color: var(--surface-strong);
  font-family: inherit;
  font-size: 1.1rem;
  font-weight: 800;
  letter-spacing: 0;
  text-shadow: none;
  text-transform: none;
  border: 0;
  padding: 0;
}

.nav-tabs,
.nav-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-tabs {
  justify-content: center;
}

.nav-right {
  justify-content: flex-end;
  flex-wrap: wrap;
}

.wallet-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wallet-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.wallet-option {
  padding: 10px 14px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--surface-strong);
  cursor: pointer;
  font-family: inherit;
  font-size: 0.86rem;
  font-weight: 800;
}

.wallet-option:hover {
  border-color: rgba(20, 125, 100, 0.35);
  color: var(--primary-dark);
}

.wallet-option.muted {
  color: var(--muted);
}

.nav-tab,
.btn-connect,
.btn-claim,
.btn-disconnect,
.btn-refresh,
.btn-primary,
.btn-outline,
.pbtn {
  border-radius: 8px;
  font-family: inherit;
  font-weight: 700;
  letter-spacing: 0;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.nav-tab {
  padding: 10px 16px;
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
  font-size: 0.92rem;
}

.nav-tab:hover,
.nav-tab.active {
  background: var(--surface-soft);
  color: var(--surface-strong);
  border-color: var(--line);
}

.btn-connect,
.btn-claim,
.btn-primary {
  background: var(--primary);
  color: #fff;
  border: 1px solid var(--primary);
  box-shadow: 0 10px 24px rgba(20, 125, 100, 0.22);
}

.btn-connect,
.btn-claim,
.btn-disconnect {
  padding: 10px 14px;
  font-size: 0.86rem;
}

.btn-disconnect {
  background: #fff;
  border: 1px solid var(--line);
  color: var(--muted);
  cursor: pointer;
  box-shadow: none;
}

.btn-disconnect:hover {
  color: var(--danger);
  border-color: rgba(194, 65, 56, 0.28);
}

.btn-claim {
  background: var(--surface-strong);
  border-color: var(--surface-strong);
}

.btn-primary {
  padding: 14px 22px;
  font-size: 0.98rem;
}

.btn-primary:hover,
.btn-connect:hover,
.btn-claim:hover {
  background: var(--primary-dark);
  color: #fff;
  border-color: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-outline,
.btn-refresh {
  background: rgba(255, 255, 255, 0.7);
  color: var(--surface-strong);
  border: 1px solid var(--line);
  box-shadow: none;
}

.btn-outline {
  padding: 14px 22px;
  font-size: 0.98rem;
}

.btn-refresh {
  padding: 10px 16px;
  font-size: 0.9rem;
}

.btn-outline:hover,
.btn-refresh:hover {
  background: var(--surface);
  border-color: rgba(20, 125, 100, 0.35);
  color: var(--primary-dark);
}

.nav-wallet,
.nav-balance {
  background: var(--surface-soft);
  border: 1px solid var(--line);
  color: var(--surface-strong);
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 0.82rem;
  font-weight: 700;
}

.back-link {
  margin: 0 0 14px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--surface-strong);
  cursor: pointer;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 800;
}

.back-link:hover {
  background: #fff;
  border-color: rgba(20, 125, 100, 0.35);
}

.tab-content {
  width: min(1160px, calc(100% - 32px));
  max-width: none;
  margin: 0 auto;
  padding: 44px 0 64px;
  animation: none;
}

.hero {
  display: grid;
  align-content: center;
  min-height: 420px;
  padding: clamp(48px, 8vw, 86px);
  overflow: hidden;
  text-align: left;
  background:
    linear-gradient(110deg, rgba(16, 56, 43, 0.96), rgba(20, 125, 100, 0.88)),
    url('https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=1600&q=80');
  background-position: center;
  background-size: cover;
  border-radius: 8px;
  box-shadow: var(--shadow);
  animation: none;
}

.hero-badge {
  width: fit-content;
  margin: 0 0 22px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 999px;
  box-shadow: none;
  color: #f7fbf8;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0;
  animation: none;
}

.hero-title,
h1,
h2 {
  color: inherit;
  font-family: inherit;
  letter-spacing: 0;
  text-shadow: none;
  text-transform: none;
}

.hero-title {
  max-width: 760px;
  margin: 0 0 18px;
  color: #fff;
  font-size: clamp(2.6rem, 7vw, 5.8rem);
  font-weight: 800;
  line-height: 0.96;
}

.hero-subtitle {
  max-width: 660px;
  margin: 0 0 30px;
  padding: 0;
  color: rgba(255, 255, 255, 0.82);
  font-family: inherit;
  font-size: clamp(1rem, 2vw, 1.22rem);
  font-weight: 500;
  line-height: 1.65;
  text-shadow: none;
  text-transform: none;
  animation: none;
}

.hero-buttons {
  justify-content: flex-start;
  gap: 12px;
  margin: 0;
  animation: none;
}

.features {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 22px 0;
}

.feature,
.match-card,
.predict-teams,
.predict-contract,
.not-on-chain,
.stat,
.empty-state {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(34, 55, 43, 0.07);
}

.feature {
  padding: 22px;
  text-align: left;
  animation: none;
}

.feature-icon {
  margin-bottom: 14px;
  padding: 6px 10px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 999px;
  box-shadow: none;
  color: var(--primary-dark);
  font-size: 0.76rem;
  letter-spacing: 0;
}

.feature-title {
  color: var(--ink);
  font-size: 1rem;
}

.feature-desc,
.stat-label,
.empty-desc,
.predict-hint,
.first-hint,
.not-on-chain p,
.predict-league,
.card-league,
.card-action,
.predict-team-label,
.pool-title,
.pool-label,
.pool-amount,
.stake-currency {
  color: var(--muted);
}

.hero .hero-subtitle {
  color: rgba(255, 255, 255, 0.9);
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  margin-top: 22px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

.stat {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  padding: 28px 18px;
}

.stat-value {
  color: var(--surface-strong);
  font-size: 2rem;
  text-shadow: none;
}

.matches-header {
  margin-bottom: 18px;
}

.matches-header h2 {
  color: var(--ink);
  font-size: clamp(1.8rem, 4vw, 2.8rem);
  font-weight: 800;
}

.loading {
  color: var(--muted);
}

.api-notice {
  margin-bottom: 16px;
  padding: 12px 14px;
  background: rgba(225, 167, 47, 0.16);
  border: 1px solid rgba(225, 167, 47, 0.34);
  border-radius: 8px;
  color: #6f4e08;
  font-size: 0.9rem;
  font-weight: 700;
  line-height: 1.5;
}

.feed-note {
  margin: -4px 0 16px;
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 600;
  line-height: 1.55;
}

.feed-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.feed-legend span {
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.feed-legend strong {
  color: var(--surface-strong);
}

.match-tools {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) repeat(4, auto);
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
}

.match-search,
.match-select {
  min-height: 42px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--ink);
}

.matches-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.match-card {
  padding: 18px;
}

.match-card:hover {
  background: #fff;
  border-color: rgba(20, 125, 100, 0.36);
  box-shadow: var(--shadow);
  transform: translateY(-2px);
}

.card-league {
  margin-bottom: 18px;
  font-size: 0.74rem;
}

.card-topline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 16px;
}

.card-topline .card-league {
  margin-bottom: 0;
}

.feed-badge {
  flex: 0 0 auto;
  padding: 5px 8px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 900;
  text-transform: uppercase;
}

.feed-badge.real {
  background: rgba(36, 138, 77, 0.1);
  color: var(--success);
}

.feed-badge.demo {
  background: rgba(225, 167, 47, 0.16);
  color: #8a620e;
}

.card-teams {
  gap: 12px;
}

.card-logo {
  width: 44px;
  height: 44px;
}

.card-name {
  color: var(--ink);
  font-size: 0.84rem;
}

.card-vs-text,
.card-score,
.predict-score {
  color: var(--surface-strong);
}

.card-status.ns,
.predict-status.ns {
  color: var(--accent);
}

.card-status.ft,
.predict-status.ft {
  color: var(--success);
}

.predict-league {
  margin-bottom: 16px;
  font-size: 0.92rem;
  font-weight: 700;
}

.predict-teams {
  padding: clamp(20px, 4vw, 34px);
}

.predict-logo {
  width: 76px;
  height: 76px;
}

.predict-team-name {
  color: var(--ink);
}

.predict-contract,
.not-on-chain {
  padding: clamp(20px, 4vw, 32px);
}

.pool-title {
  font-weight: 800;
}

.pool-track {
  height: 8px;
  background: var(--surface-soft);
}

.pool-fill.home {
  background: var(--success);
}

.pool-fill.draw {
  background: var(--accent);
}

.pool-fill.away {
  background: var(--danger);
}

.stake-input-row {
  flex-wrap: wrap;
}

.stake-input {
  width: 160px;
  background: #fff;
  border: 1px solid var(--line);
  color: var(--ink);
}

.odds-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.odd-box {
  background: var(--surface-soft);
  border: 1px solid var(--line);
  color: var(--muted);
  line-height: 1.5;
}

.odd-box strong {
  color: var(--surface-strong);
}

.predict-btns {
  gap: 10px;
}

.pbtn {
  min-height: 54px;
  border-width: 1px;
}

.pbtn.home {
  background: rgba(36, 138, 77, 0.1);
  border-color: rgba(36, 138, 77, 0.24);
  color: #176339;
}

.pbtn.draw {
  background: rgba(225, 167, 47, 0.14);
  border-color: rgba(225, 167, 47, 0.28);
  color: #8a620e;
}

.pbtn.away {
  background: rgba(194, 65, 56, 0.1);
  border-color: rgba(194, 65, 56, 0.24);
  color: #92312b;
}

.pbtn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(34, 55, 43, 0.09);
}

.result-banner {
  background: rgba(36, 138, 77, 0.1);
  border-color: rgba(36, 138, 77, 0.2);
  color: var(--success);
}

.prediction-list {
  display: grid;
  gap: 12px;
}

.insight-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 18px;
}

.insight-panel {
  padding: 20px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(34, 55, 43, 0.07);
}

.panel-title {
  margin-bottom: 14px;
  color: var(--ink);
  font-size: 1rem;
  font-weight: 900;
}

.panel-empty {
  color: var(--muted);
  font-size: 0.92rem;
}

.leader-row,
.verify-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--line);
}

.leader-row:first-of-type,
.verify-row:first-of-type {
  border-top: 0;
}

.leader-row strong,
.verify-row strong {
  color: var(--surface-strong);
}

.leader-row span,
.verify-row span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.prediction-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  align-items: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(34, 55, 43, 0.07);
}

.prediction-league {
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

.prediction-title {
  color: var(--ink);
  font-size: 1.1rem;
  font-weight: 800;
}

.prediction-choice {
  margin-top: 6px;
  color: var(--primary-dark);
  font-weight: 800;
}

.prediction-metrics,
.confirm-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.prediction-metrics div,
.confirm-grid div {
  min-width: 120px;
  padding: 12px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.prediction-metrics span,
.confirm-grid span {
  display: block;
  margin-bottom: 5px;
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 800;
}

.prediction-metrics strong,
.confirm-grid strong {
  color: var(--surface-strong);
  font-size: 0.92rem;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(10, 20, 16, 0.56);
  backdrop-filter: blur(6px);
}

.confirm-modal {
  width: min(520px, 100%);
  padding: 24px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 24px 70px rgba(10, 20, 16, 0.25);
}

.modal-kicker {
  margin-bottom: 8px;
  color: var(--primary-dark);
  font-size: 0.78rem;
  font-weight: 900;
  text-transform: uppercase;
}

.confirm-modal h2 {
  margin-bottom: 12px;
  color: var(--ink);
  font-size: 1.8rem;
  font-weight: 800;
}

.confirm-modal p {
  margin-bottom: 16px;
  color: var(--muted);
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.msg {
  border-radius: 8px;
  font-weight: 700;
}

.msg.info {
  background: rgba(20, 125, 100, 0.1);
  border-color: rgba(20, 125, 100, 0.22);
  color: var(--primary-dark);
}

.msg.success {
  background: rgba(36, 138, 77, 0.1);
  border-color: rgba(36, 138, 77, 0.2);
  color: var(--success);
}

.msg.error {
  background: rgba(194, 65, 56, 0.1);
  border-color: rgba(194, 65, 56, 0.22);
  color: var(--danger);
}

@media (max-width: 900px) {
  .navbar {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .nav-tabs,
  .nav-right {
    justify-content: flex-start;
    width: 100%;
    overflow-x: auto;
  }

  .features,
  .matches-grid,
  .odds-row {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .tab-content {
    width: 100%;
    padding: 18px 12px 40px;
  }

  .navbar {
    position: relative;
    padding: 12px;
    min-height: 0;
    box-shadow: 0 8px 24px rgba(20, 33, 27, 0.08);
  }

  .nav-logo {
    font-size: 1rem;
  }

  .nav-tabs,
  .nav-right {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    overflow: visible;
  }

  .nav-right {
    grid-template-columns: 1fr;
  }

  .wallet-group {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
    width: 100%;
  }

  .wallet-picker {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
    width: 100%;
  }

  .nav-tab,
  .btn-connect,
  .btn-claim,
  .btn-disconnect,
  .wallet-option,
  .nav-wallet,
  .nav-balance {
    width: 100%;
    min-width: 0;
    padding: 10px 8px;
    text-align: center;
    white-space: nowrap;
    font-size: 0.78rem;
  }

  .hero {
    min-height: auto;
    padding: 34px 18px;
    border-radius: 0;
    margin-inline: -12px;
  }

  .hero-title {
    font-size: clamp(2.2rem, 14vw, 3.45rem);
    line-height: 1;
  }

  .hero-subtitle {
    font-size: 0.98rem;
    line-height: 1.55;
  }

  .hero-buttons,
  .predict-btns,
  .predict-teams,
  .pool-bar {
    flex-direction: column;
  }

  .hero-buttons .btn-primary,
  .hero-buttons .btn-outline,
  .predict-btns .pbtn {
    width: 100%;
  }

  .features,
  .matches-grid,
  .stats,
  .odds-row,
  .prediction-card,
  .prediction-metrics,
  .confirm-grid,
  .match-tools,
  .insight-grid {
    grid-template-columns: 1fr;
  }

  .feature,
  .match-card,
  .predict-teams,
  .predict-contract,
  .not-on-chain,
  .empty-state {
    padding: 18px;
  }

  .matches-header {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  .matches-header h2 {
    font-size: 1.75rem;
  }

  .feed-legend {
    display: grid;
    grid-template-columns: 1fr;
  }

  .btn-refresh {
    width: 100%;
  }

  .card-teams {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 8px;
  }

  .card-logo {
    width: 38px;
    height: 38px;
  }

  .card-name,
  .predict-team-name {
    overflow-wrap: anywhere;
  }

  .predict-score {
    padding: 16px 0;
    font-size: 1.6rem;
  }

  .predict-logo {
    width: 64px;
    height: 64px;
  }

  .stake-input-row {
    align-items: stretch;
    display: grid;
    grid-template-columns: 1fr;
  }

  .stake-input {
    width: 100%;
  }

  .modal-actions {
    flex-direction: column-reverse;
  }

  .modal-actions button {
    width: 100%;
  }

  .pool-label,
  .pool-amount {
    width: 100%;
    text-align: left;
  }
}

@media (max-width: 380px) {
  .nav-tab,
  .btn-connect,
  .btn-claim,
  .btn-disconnect,
  .wallet-option,
  .nav-wallet,
  .nav-balance {
    font-size: 0.72rem;
    padding-inline: 6px;
  }

  .hero-title {
    font-size: 2rem;
  }

  .card-teams {
    grid-template-columns: 1fr;
  }

  .card-vs {
    order: -1;
  }
}
</style>
