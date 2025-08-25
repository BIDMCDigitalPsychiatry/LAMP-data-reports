import { useState } from "react";
import "../style/Login.css";

const handleSubmit = () => {
  console.log('submit')
}

export default function Admin() {
  const [email, setEmail] = useState("");

  return (
    <div className = 'login_container'>
      <form onSubmit={handleSubmit} className = 'login-form'>
        <h1>Admin</h1>
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