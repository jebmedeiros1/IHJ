import { useState } from 'react'

function App() {
  const [classes, setClasses] = useState([])

  async function loadClasses() {
    const res = await fetch('http://localhost:8000/classes')
    const data = await res.json()
    setClasses(data)
  }

  return (
    <div>
      <h1>IHJ Busca de Equipamentos</h1>
      <button onClick={loadClasses}>Carregar Classes</button>
      <ul>
        {classes.map(c => <li key={c}>{c}</li>)}
      </ul>
    </div>
  )
}

export default App
