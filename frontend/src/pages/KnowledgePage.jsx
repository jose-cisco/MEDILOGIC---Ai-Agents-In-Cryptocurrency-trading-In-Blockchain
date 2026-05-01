import { useState, useEffect, useRef } from 'react'
import { API_BASE } from '../App'

const TAB_JSON = 'json'
const TAB_FILE = 'file'
const TAB_URL = 'url'

export default function KnowledgePage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeIngestTab, setActiveIngestTab] = useState(TAB_JSON)

  // JSON / text ingestion
  const [newDocs, setNewDocs] = useState('[\n  {"text": "Sample market intelligence content...", "source": "Manual Ingest"}\n]')
  const [ingesting, setIngesting] = useState(false)
  const [ingestResult, setIngestResult] = useState(null)

  // File upload
  const [dragOver, setDragOver] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [fileSource, setFileSource] = useState('Research Report')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  // URL scraping
  const [websiteUrls, setWebsiteUrls] = useState('https://www.coindesk.com/\nhttps://cointelegraph.com/')
  const [scrapeTask, setScrapeTask] = useState('Scrape the latest crypto market news and extract actionable stories about Bitcoin, Ethereum, Solana, DeFi, ETF flows, regulation, and on-chain risk signals.')
  const [scrapeSource, setScrapeSource] = useState('Autonomous Web News')
  const [scrapeMaxPages, setScrapeMaxPages] = useState(4)
  const [scraping, setScraping] = useState(false)

  // Search
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/knowledge/stats`)
      const data = await res.json()
      setStats(data)
    } catch (e) {
      console.error('Failed to fetch stats', e)
    }
    setLoading(false)
  }

  useEffect(() => { fetchStats() }, [])

  // ── JSON ingest ────────────────────────────────────────────────────────────
  const handleIngest = async () => {
    setIngesting(true)
    setIngestResult(null)
    try {
      const docs = JSON.parse(newDocs)
      const res = await fetch(`${API_BASE}/knowledge/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ documents: docs }),
      })
      const data = await res.json()
      setIngestResult({ ok: data.status === 'success', msg: data.status === 'success' ? `✅ Ingested ${docs.length} document(s)` : `❌ ${data.detail}` })
      if (data.status === 'success') fetchStats()
    } catch (e) {
      setIngestResult({ ok: false, msg: `❌ JSON parse error: ${e.message}` })
    }
    setIngesting(false)
  }

  // ── File upload ────────────────────────────────────────────────────────────
  const handleFileDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files).filter(f => /\.(pdf|txt)$/i.test(f.name))
    setSelectedFiles(prev => [...prev, ...files])
  }

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files)
    setSelectedFiles(prev => [...prev, ...files])
  }

  const removeFile = (idx) => setSelectedFiles(prev => prev.filter((_, i) => i !== idx))

  const handleUpload = async () => {
    if (!selectedFiles.length) return
    setUploading(true)
    setIngestResult(null)
    try {
      const formData = new FormData()
      selectedFiles.forEach(f => formData.append('files', f))
      formData.append('source', fileSource)
      const res = await fetch(`${API_BASE}/knowledge/upload`, { method: 'POST', body: formData })
      const data = await res.json()
      const ok = data.ingested_count > 0
      const msgs = []
      if (data.ingested_files?.length) msgs.push(`✅ Ingested: ${data.ingested_files.join(', ')}`)
      if (data.errors?.length) msgs.push(`⚠️ Errors: ${data.errors.join(' | ')}`)
      setIngestResult({ ok, msg: msgs.join('\n') || (ok ? 'Done' : '❌ Failed') })
      if (ok) { setSelectedFiles([]); fetchStats() }
    } catch (e) {
      setIngestResult({ ok: false, msg: `❌ Upload failed: ${e.message}` })
    }
    setUploading(false)
  }

  // ── URL scraper ───────────────────────────────────────────────────────────
  const handleScrape = async () => {
    const urls = websiteUrls
      .split('\n')
      .map((url) => url.trim())
      .filter(Boolean)

    if (!urls.length || !scrapeTask.trim()) return

    setScraping(true)
    setIngestResult(null)
    try {
      const res = await fetch(`${API_BASE}/knowledge/scrape-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls,
          task: scrapeTask,
          source_label: scrapeSource,
          max_pages: scrapeMaxPages,
        }),
      })
      const data = await res.json()
      const ok = data.status === 'success' && data.ingested_count > 0
      const pageCount = data.scraped_pages?.length ?? 0
      const messages = []
      if (ok) messages.push(`✅ Scraped ${pageCount} page(s) and ingested ${data.ingested_count} document(s) into ChromaDB`)
      if (data.scraped_pages?.length) messages.push(`Pages: ${data.scraped_pages.map((page) => page.title || page.url).join(', ')}`)
      if (data.errors?.length) messages.push(`⚠️ Errors: ${data.errors.join(' | ')}`)
      setIngestResult({ ok, msg: messages.join('\n') || '❌ No documents were extracted from the supplied URLs' })
      if (ok) fetchStats()
    } catch (e) {
      setIngestResult({ ok: false, msg: `❌ URL scraping failed: ${e.message}` })
    }
    setScraping(false)
  }

  // ── Search ─────────────────────────────────────────────────────────────────
  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const res = await fetch(`${API_BASE}/knowledge/hybrid-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, n_results: 5 }),
      })
      setSearchResults(await res.json())
    } catch (e) { alert('Search failed: ' + e.message) }
    setSearching(false)
  }

  const TabBtn = ({ id, label }) => (
    <button
      onClick={() => { setActiveIngestTab(id); setIngestResult(null) }}
      style={{
        padding: '8px 18px',
        borderRadius: '8px 8px 0 0',
        border: 'none',
        cursor: 'pointer',
        fontWeight: 600,
        fontSize: 13,
        background: activeIngestTab === id ? 'var(--bg-card)' : 'transparent',
        color: activeIngestTab === id ? 'var(--accent-blue)' : 'var(--text-secondary)',
        borderBottom: activeIngestTab === id ? '2px solid var(--accent-blue)' : '2px solid transparent',
        transition: 'all 0.2s',
      }}
    >{label}</button>
  )

  if (loading) return <div className="text-center py-16">Loading knowledge base...</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Knowledge Base (RAG)</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Hybrid Search (Semantic + BM25) • Reciprocal Rank Fusion • ChromaDB Vector Store
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Stats Panel */}
        <div className="card space-y-4">
          <h2 className="font-semibold text-lg">Collection Status</h2>
          <div className="space-y-3">
            {[
              { label: 'Total Documents', value: stats?.total_documents ?? stats?.count ?? 0, big: true },
              { label: 'BM25 Index', value: `${stats?.bm25_index_size ?? 0} keywords` },
              { label: 'Vector Engine', value: 'ChromaDB (Local)' },
              { label: 'Status', value: stats?.status ?? 'unknown' },
              { label: 'Hybrid Retrieval', value: stats?.hybrid_retrieval ? 'Active ✓' : 'Inactive' },
            ].map(({ label, value, big }) => (
              <div key={label} className="p-3 rounded-lg" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</div>
                <div className={big ? 'text-2xl font-bold' : 'text-sm font-medium'}>{String(value)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Ingest Panel */}
        <div className="md:col-span-2 card">
          <div className="flex gap-1 mb-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <TabBtn id={TAB_JSON} label="📝 JSON / Text Input" />
            <TabBtn id={TAB_FILE} label="📁 File Upload (PDF / TXT)" />
            <TabBtn id={TAB_URL} label="🌐 URL News Scraper" />
          </div>

          {activeIngestTab === TAB_JSON && (
            <div className="space-y-3">
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Paste a JSON array of <code>{"{ text, source }"}</code> objects to ingest directly.
              </p>
              <textarea
                rows={8}
                value={newDocs}
                onChange={(e) => setNewDocs(e.target.value)}
                className="w-full font-mono text-xs p-3 rounded-lg"
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', resize: 'vertical' }}
              />
              <button onClick={handleIngest} disabled={ingesting} className="btn-primary w-full">
                {ingesting ? 'Processing...' : '🚀 Ingest JSON Documents'}
              </button>
            </div>
          )}

          {activeIngestTab === TAB_FILE && (
            <div className="space-y-4">
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Upload <strong>PDF</strong> or <strong>TXT</strong> files. Text is extracted, chunked and embedded automatically. Drop multiple files at once.
              </p>

              {/* Source label */}
              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Source Label</label>
                <input
                  type="text"
                  value={fileSource}
                  onChange={(e) => setFileSource(e.target.value)}
                  placeholder="e.g. Research Report, News Article..."
                  className="w-full"
                />
              </div>

              {/* Drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: `2px dashed ${dragOver ? 'var(--accent-blue)' : 'var(--border)'}`,
                  borderRadius: 12,
                  padding: '32px 20px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: dragOver ? 'rgba(59,130,246,0.05)' : 'var(--bg-secondary)',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ fontSize: 36, marginBottom: 8 }}>📂</div>
                <div className="text-sm font-medium">Drag & drop PDF / TXT files here</div>
                <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>or click to browse</div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.txt"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
              </div>

              {/* File list */}
              {selectedFiles.length > 0 && (
                <div className="space-y-2">
                  {selectedFiles.map((f, i) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded-lg text-xs" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                      <div className="flex items-center gap-2">
                        <span>{f.name.endsWith('.pdf') ? '📄' : '📃'}</span>
                        <span className="font-medium">{f.name}</span>
                        <span style={{ color: 'var(--text-secondary)' }}>({(f.size / 1024).toFixed(1)} KB)</span>
                      </div>
                      <button onClick={() => removeFile(i)} style={{ color: 'var(--accent-red)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700 }}>✕</button>
                    </div>
                  ))}
                </div>
              )}

              <button onClick={handleUpload} disabled={uploading || !selectedFiles.length} className="btn-primary w-full">
                {uploading ? `Uploading ${selectedFiles.length} file(s)...` : `🚀 Upload & Ingest ${selectedFiles.length} File(s)`}
              </button>
            </div>
          )}

          {activeIngestTab === TAB_URL && (
            <div className="space-y-4">
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Add one or more website URLs and tell the autonomous scraper what news to extract. The backend will fetch the pages, let the AI structure relevant stories, and store the resulting news documents in ChromaDB.
              </p>

              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Website URL(s)</label>
                <textarea
                  rows={4}
                  value={websiteUrls}
                  onChange={(e) => setWebsiteUrls(e.target.value)}
                  placeholder="One URL per line"
                  className="w-full font-mono text-xs p-3 rounded-lg"
                  style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', resize: 'vertical' }}
                />
              </div>

              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Scraping Task</label>
                <textarea
                  rows={5}
                  value={scrapeTask}
                  onChange={(e) => setScrapeTask(e.target.value)}
                  placeholder="Describe what the AI scraper should extract from the supplied websites"
                  className="w-full text-sm p-3 rounded-lg"
                  style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', resize: 'vertical' }}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Source Label</label>
                  <input
                    type="text"
                    value={scrapeSource}
                    onChange={(e) => setScrapeSource(e.target.value)}
                    placeholder="Autonomous Web News"
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Max Pages Per Seed URL</label>
                  <input
                    type="number"
                    min="1"
                    max="8"
                    value={scrapeMaxPages}
                    onChange={(e) => setScrapeMaxPages(Number(e.target.value) || 1)}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="p-3 rounded-lg text-xs" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                Example task: <strong>Scrape the latest crypto market news, keep only fresh high-signal items about BTC, ETH, SOL, ETFs, regulation, hacks, and DeFi liquidity, then prepare them for RAG ingestion.</strong>
              </div>

              <button onClick={handleScrape} disabled={scraping || !websiteUrls.trim() || !scrapeTask.trim()} className="btn-primary w-full">
                {scraping ? 'Scraping websites and ingesting news...' : '🚀 Scrape URL(s) & Ingest News'}
              </button>
            </div>
          )}

          {/* Feedback */}
          {ingestResult && (
            <div
              className="mt-3 p-3 rounded-lg text-xs whitespace-pre-line"
              style={{
                background: ingestResult.ok ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                border: `1px solid ${ingestResult.ok ? 'var(--accent-green)' : 'var(--accent-red)'}`,
                color: ingestResult.ok ? 'var(--accent-green)' : 'var(--accent-red)',
              }}
            >
              {ingestResult.msg}
            </div>
          )}
        </div>
      </div>

      {/* Query Tester */}
      <div className="card space-y-4">
        <h2 className="font-semibold text-lg">Hybrid Query Test Bench</h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search knowledge base with hybrid retrieval…"
            className="flex-1"
          />
          <button onClick={handleSearch} disabled={searching} className="btn-primary px-8">
            {searching ? 'Searching…' : 'Search'}
          </button>
        </div>

        {searchResults && (
          <div className="space-y-3">
            <div className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
              Found {searchResults.result_count} result(s) via <em>{searchResults.retrieval_mode}</em>
            </div>
            <div className="space-y-2">
              {searchResults.results?.map((res, i) => (
                <div key={i} className="p-3 rounded-lg text-sm" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-medium" style={{ color: 'var(--accent-blue)' }}>
                      {res.metadata?.filename || res.metadata?.source || 'Unknown source'}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-blue)' }}>
                      RRF {res.rrf_score?.toFixed(4)}
                    </span>
                  </div>
                  <div className="text-xs opacity-80 line-clamp-3">{res.text}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
