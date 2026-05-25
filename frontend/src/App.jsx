import { useState } from 'react'
import './App.css'

function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)

  async function handleSearch(e) {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setResults(null)
    setSearched(true)

    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setResults(data.results)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`app${searched ? ' has-results' : ''}`}>
      <div className="content">
        <div className="hero">
          <h1>Search</h1>
          <p className="subtitle">ERCOT document search</p>
        </div>

        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            className="search-input"
          />
          <button type="submit" className="search-btn">Search</button>
        </form>
      </div>

      {error && <p className="error">{error}</p>}

      {loading && <p className="loading">Loading...</p>}

      {results && results.length === 0 && (
        <p className="no-results">No results found.</p>
      )}

      {results && results.length > 0 && (
        <div className="results-container">
          <div className="results-header">{results.length} results</div>
          <ul className="results">
            {results.map((r, i) => (
              <li key={i} className="result-item">
                <a href={r.url} className="result-title" target="_blank" rel="noopener noreferrer">
                  {r.title}
                </a>
                <span className="result-url">{r.url}</span>
                <p className="result-body">{r.body}</p>
                <span className="result-score">Score: {r.score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default App