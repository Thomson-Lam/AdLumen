"use client"

import { useState } from "react"
import { Send, Search, Home, HelpCircle, DollarSign, LogIn, Shield, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Image from "next/image"

export default function AdLumenScanner() {
  const [url, setUrl] = useState("")
  const [isScanning, setIsScanning] = useState(false)
  const [result, setResult] = useState<string | null>("");
  const [error, setError] = useState<string | null>(null); 

  const handleScan = async(e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsScanning(true);
    setError(null);
    try{
        const response = await fetch('http://localhost:8000/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        if (!response.ok) {
          throw new Error('Failed to fetch URL');
        } 
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsScanning(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Navigation Header */}
      <header className="w-full px-6 py-4 bg-slate-900/50 backdrop-blur-sm border-b border-blue-500/20">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Navigation Links */}
          <nav className="flex items-center space-x-8">
            <Button
              variant="ghost"
              className="text-white hover:text-blue-400 hover:bg-blue-500/10 transition-all duration-200"
            >
              <Home className="w-4 h-4 mr-2" />
              Home
            </Button>
            <Button
              variant="ghost"
              className="text-white hover:text-blue-400 hover:bg-blue-500/10 transition-all duration-200"
            >
              <HelpCircle className="w-4 h-4 mr-2" />
              How Does It Work
            </Button>
            <Button
              variant="ghost"
              className="text-white hover:text-blue-400 hover:bg-blue-500/10 transition-all duration-200"
            >
              <DollarSign className="w-4 h-4 mr-2" />
              Pricing
            </Button>
            <Button
              variant="ghost"
              className="text-white hover:text-blue-400 hover:bg-blue-500/10 transition-all duration-200"
            >
              <LogIn className="w-4 h-4 mr-2" />
              Login
            </Button>
          </nav>

          {/* Logo */}
          <div className="flex items-center">
            <Image src="/images/adlumen-logo.png" alt="AdLumen Logo" width={200} height={60} className="h-12 w-auto" />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        {/* Hero Section */}
        <div className="text-center mb-16 max-w-4xl">
          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
            Detect Malicious Websites
          </h1>
          <p className="text-xl md:text-2xl text-blue-200 mb-8 leading-relaxed">
            Protect yourself from malicious websites and online scams with our advanced AI detection technology
          </p>

          {/* Feature Highlights */}
          <div className="flex flex-wrap justify-center gap-6 mb-12">
            <div className="flex items-center bg-blue-500/10 backdrop-blur-sm rounded-full px-4 py-2 border border-blue-500/20">
              <Shield className="w-5 h-5 text-blue-400 mr-2" />
              <span className="text-blue-200">Real-time Scanning</span>
            </div>
            <div className="flex items-center bg-blue-500/10 backdrop-blur-sm rounded-full px-4 py-2 border border-blue-500/20">
              <Zap className="w-5 h-5 text-blue-400 mr-2" />
              <span className="text-blue-200">AI-Powered Detection</span>
            </div>
            <div className="flex items-center bg-blue-500/10 backdrop-blur-sm rounded-full px-4 py-2 border border-blue-500/20">
              <Search className="w-5 h-5 text-blue-400 mr-2" />
              <span className="text-blue-200">Threat Analysis</span>
            </div>
          </div>
        </div>

        {/* URL Scanner Interface */}
        <div className="w-full max-w-2xl">
          <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-blue-500/20 shadow-2xl">
            <div className="relative">
              <div className="flex items-center space-x-4">
                <div className="flex-1 relative">
                  <Input
                    type="url"
                    placeholder="Enter URL to scan for malicious content..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="w-full h-16 px-6 text-lg bg-white border-2 border-blue-200 rounded-xl focus:border-blue-400 focus:ring-4 focus:ring-blue-400/20 transition-all duration-200 placeholder:text-gray-500"
                    disabled={isScanning}
                  />
                  {isScanning && (
                    <div className="absolute inset-0 bg-blue-500/10 rounded-xl flex items-center justify-center">
                      <div className="flex items-center space-x-3">
                        <div className="w-6 h-6 border-3 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-blue-400 font-medium">Scanning...</span>
                      </div>
                    </div>
                  )}
                </div>

                <Button
                  onClick={(e) =>handleScan}
                  disabled={!url.trim() || isScanning}
                  className="h-16 w-16 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 border-0 rounded-xl shadow-lg hover:shadow-blue-500/25 transition-all duration-200 group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="w-6 h-6 text-white group-hover:scale-110 transition-transform duration-200" />
                </Button>
              </div>
            </div>

            {/* Scan Progress */}
            {isScanning && (
              <div className="mt-6">
                <div className="w-full bg-blue-900/30 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-blue-400 to-cyan-400 h-2 rounded-full animate-pulse"
                    style={{ width: "60%" }}
                  ></div>
                </div>
                <p className="text-blue-300 text-sm mt-2 text-center">
                  Analyzing content for malicious websites and online scams...
                </p>
              </div>
            )}


            {error && (
              <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
                {error}
              </div>
            )}

            {result && (
              <div className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400">
                {result}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="mt-8 text-center">
            <p className="text-blue-300 mb-4">Try these examples:</p>
            <div className="flex flex-wrap justify-center gap-3">
              {["amazon.com", "ebay.com", "facebook.com/marketplace"].map((example) => (
                <Button
                  key={example}
                  variant="outline"
                  size="sm"
                  onClick={() => setUrl(`https://${example}`)}
                  className="bg-blue-500/10 text-blue-300 border-blue-500/30 hover:bg-blue-500/20 hover:border-blue-400 transition-all duration-200"
                  disabled={isScanning}
                >
                  {example}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Trust Indicators */}
        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl w-full">
          <div className="text-center p-6 bg-blue-500/5 rounded-xl border border-blue-500/10">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">94% Accuracy</h3>
            <p className="text-blue-200">Advanced AI models trained on large dataset on scam patterns</p>
          </div>

          <div className="text-center p-6 bg-blue-500/5 rounded-xl border border-blue-500/10">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Instant Results</h3>
            <p className="text-blue-200">Get comprehensive scan results in under 3 seconds</p>
          </div>

          <div className="text-center p-6 bg-blue-500/5 rounded-xl border border-blue-500/10">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Threat Detection</h3>
            <p className="text-blue-200">Identify phishing, malware, and other malicious activities.</p>
          </div>
        </div>
      </main>
    </div>
  )
}
