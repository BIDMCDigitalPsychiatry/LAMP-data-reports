import "../style/Login.css"

const handleSubmit = () => {
  console.log('submit')
}

export default function Login() {
  
  return (
    <div className = 'login_container'>
      <h1>MIND-lab</h1>
      <form onSubmit={handleSubmit}>
        <input 
          type="email"
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
        />
        <br />
        <input 
          type="password"
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Password"
        />
        <br />
        <input type="submit" value="Login" />
      </form>
    </div>
  )
}