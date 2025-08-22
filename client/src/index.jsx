import DataReport from "./components/DataReport";
import * as ReactDOMClient from "react-dom/client";
import Login from "./components/Login";
import Admin from "./components/Admin"
import React from "react";
import {BrowserRouter, Routes, Route} from "react-router-dom";
import "./index.css"

const container = document.getElementById("root");
const root = ReactDOMClient.createRoot(container);

root.render(
  <BrowserRouter>
    <Routes>
      <Route path = "/" element = {<Login />}/>
      <Route path = "/admin" element = {<Admin />}/>
    </Routes>
  </BrowserRouter>
)