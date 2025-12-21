import React from 'react'
import { Layout } from 'antd'
import Explorer from './components/Explorer'
import './App.css'

const { Header, Content } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ 
        background: '#001529', 
        color: 'white', 
        display: 'flex', 
        alignItems: 'center',
        padding: '0 24px'
      }}>
        <h1 style={{ color: 'white', margin: 0 }}>mABC Blockchain Explorer</h1>
      </Header>
      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        <Explorer />
      </Content>
    </Layout>
  )
}

export default App

