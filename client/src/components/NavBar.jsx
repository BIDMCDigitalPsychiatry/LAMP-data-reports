import "../style/NavBar.css"

export default function NavBar() {
  <div className = 'NavBar_container'>
    <nav>
      <ul>
        <Link to= "/app/dashboard">Dashboard</Link>
      </ul>
      <ul>
        <Link to = "/app/datareport">Data Report</Link>
      </ul>
      <ul>
        <Link to = "/app/patient">Patient</Link>
      </ul>
    </nav>
  </div>
}