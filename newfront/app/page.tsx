"use client"

import { useState } from "react"
import { Send, Search, Home, HelpCircle, DollarSign, LogIn, Shield, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Image from "next/image"

type Res  = {
	url: string;
  	fraud_probability: number;
  	confidence_level: number;
  	justification: string;
};

function evalRisk(result: Res): "low" | "medium" | "high" {
  if (result.confidence_level >= 8 || result.fraud_probability >= 70) {
    return "high";
  } else if (result.confidence_level >= 5 || result.fraud_probability >= 50) {
    return "medium";
  } else {
    return "low";
  }
}

export default function AdLumenScanner() {
  const [url, setUrl] = useState("")
  const [isScanning, setIsScanning] = useState(false)
  const [result, setResult] = useState<Res | null>(null);
  const [error, setError] = useState<string | null>(null); 

  const handleScan = async() => {
	console.log("WORKING");
    //e.preventDefault();
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
	const post_res: Res = await response.json(); // TODO: Check if this works!
	setResult(post_res);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsScanning(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br via-blue-900 from-slate-900 to-slate-900">
      {/* Navigation Header */}
      <header className="py-4 px-6 w-full border-b bg-slate-900/50 backdrop-blur-sm border-blue-500/20">
        <div className="flex justify-between items-center mx-auto max-w-7xl">
          {/* Navigation Links */}
          <nav className="flex items-center space-x-8">
            <Button
              variant="ghost"
              className="text-white transition-all duration-200 hover:text-blue-400 hover:bg-blue-500/10"
            >
              <Home className="mr-2 w-4 h-4" />
              Home
            </Button>
            <Button
              variant="ghost"
              className="text-white transition-all duration-200 hover:text-blue-400 hover:bg-blue-500/10"
            >
              <HelpCircle className="mr-2 w-4 h-4" />
              How Does It Work?
            </Button>
            <Button
              variant="ghost"
              className="text-white transition-all duration-200 hover:text-blue-400 hover:bg-blue-500/10"
            >
              <DollarSign className="mr-2 w-4 h-4" />
              Pricing
            </Button>
            <Button
              variant="ghost"
              className="text-white transition-all duration-200 hover:text-blue-400 hover:bg-blue-500/10"
            >
              <LogIn className="mr-2 w-4 h-4" />
              Login
            </Button>
          </nav>

          {/* Logo */}
          <div className="flex items-center">
            <Image src="/images/adlumen-logo.png" alt="AdLumen Logo" width={200} height={60} className="w-auto h-12" />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex flex-col flex-1 justify-center items-center py-20 px-6">
        {/* Hero Section */}
        <div className="mb-16 max-w-4xl text-center">
          <h1 className="mb-6 text-5xl font-bold text-transparent text-white bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300 md:text-7xl">
            Detect Scam Websites
          </h1>
          <p className="mb-8 text-xl leading-relaxed text-white md:text-2xl">
            Hi 🤗 Paste a URL to scan the site, or use one of the URLs below. 
          </p>

          {/* Feature Highlights */}
          <div className="flex flex-wrap gap-6 justify-center mb-12">
            <div className="flex items-center py-2 px-4 rounded-full border bg-blue-500/10 backdrop-blur-sm border-blue-500/20">
              <Shield className="mr-2 w-5 h-5 text-blue-400" />
              <span className="text-xl font-bold text-white">Semantic + Element Scanning</span>
            </div>
            <div className="flex items-center py-2 px-4 rounded-full border bg-blue-500/10 backdrop-blur-sm border-blue-500/20">
              <Zap className="mr-2 w-5 h-5 text-blue-400" />
              <span className="text-xl font-bold text-white">Domain Analysis</span>
            </div>
            <div className="flex items-center py-2 px-4 rounded-full border bg-blue-500/10 backdrop-blur-sm border-blue-500/20">
              <Search className="mr-2 w-5 h-5 text-blue-400" />
              <span className="text-xl font-bold text-white">ID deceptive Ads and browse safely</span>
            </div>
          </div>
        </div>

        {/* URL Scanner Interface */}
        <div className="w-full max-w-2xl">
          <div className="p-8 rounded-2xl border shadow-2xl bg-white/5 backdrop-blur-lg border-blue-500/20">
            <div className="relative">
              <div className="flex items-center space-x-4">
                <div className="relative flex-1">
                  <Input
                    type="url"
                    placeholder="Enter URL to scan for malicious content..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="px-6 w-full h-16 text-lg bg-white rounded-xl border-2 border-blue-200 transition-all duration-200 focus:border-blue-400 focus:ring-4 placeholder:text-gray-500 focus:ring-blue-400/20"
                    disabled={isScanning}
                  />
                  {isScanning && (
                    <div className="flex absolute inset-0 justify-center items-center rounded-xl bg-blue-500/10">
                      <div className="flex items-center space-x-3">
                        <div className="w-6 h-6 rounded-full border-blue-400 animate-spin border-3 border-t-transparent"></div>
                        <span className="font-medium text-blue-400">Scanning...</span>
                      </div>
                    </div>
                  )}
                </div>

                <Button
                  onClick={handleScan}
                  disabled={!url.trim() || isScanning}
                  className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl border-0 shadow-lg transition-all duration-200 hover:from-blue-600 hover:to-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed group hover:shadow-blue-500/25"
                >
                  <Send className="w-6 h-6 text-white transition-transform duration-200 group-hover:scale-110" />
                </Button>
              </div>
            </div>

            {/* Scan Progress */}
            {isScanning && (
              <div className="mt-6">
                <div className="w-full h-2 rounded-full bg-blue-900/30">
                  <div
                    className="h-2 bg-gradient-to-r from-blue-400 to-cyan-400 rounded-full animate-pulse"
                    style={{ width: "60%" }}
                  ></div>
                </div>
                <p className="mt-2 text-sm text-center text-blue-300">
                  Analyzing content for malicious websites and online scams...
                </p>
              </div>
            )}


            {error && (
              <div className="p-4 mt-4 text-red-400 rounded-lg border bg-red-500/10 border-red-500/20">
                {error}
              </div>
            )}

            {result && (
		<div className="flex flex-col gap-y-1 justify-center items-center mt-5 w-full rounded-lg border bg-blue/60">
			<div className="flex flex-row justify-between items-center p-4 w-full text-white">
			<h2 className="text-xl font-bold">Security Risk: {evalRisk(result).toUpperCase()}</h2>
			
			</div>
              		<div className="flex flex-row justify-between items-center p-4 w-full text-white border-t border-white">
			<p className="font-bold">AI Confidence Level (out of 10):</p>
			<p className={
    				result.confidence_level >= 8
      				? 'rounded-lg bg-red-700/30 text-red-700'
      				: result.confidence_level >= 5
      				? 'rounded-lg bg-yellow-700/30 text-yellow-700'
      				: 'rounded-lg bg-green-700/30 text-green-300 px-2'}>
    			{result.confidence_level}</p>
              		</div>
			<div className="flex flex-row justify-between items-center p-4 w-full text-white border-t border-white">
				<p className="font-bold">Fraud Probability (out of 100):</p>
				<p className={
    					result.fraud_probability >= 70
      					? 'rounded-lg bg-red-700/30 text-red-700'
      					: result.fraud_probability >= 50
      					? 'rounded-lg bg-yellow-700/30 text-yellow-700'
      					: 'rounded-lg bg-green-700/30 text-green-300 px-2'}>
    				{result.fraud_probability} %</p>
              		</div>
			<div className="flex flex-col items-center p-4 w-full text-white border-t border-white">
				<h2 className="text-xl font-bold">Justification:</h2>
                		<p className="p-2 text-center">{result.justification}</p>
              		</div>
			
		</div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="mt-8 text-center">
            <p className="mb-4 text-blue-300">Try these examples:</p>
            <div className="flex flex-wrap gap-3 justify-center">
              {["amazon.com", "ebay.com", "facebook.com/marketplace"].map((example) => (
                <Button
                  key={example}
                  variant="outline"
                  size="sm"
                  onClick={() => setUrl(`https://${example}`)}
                  className="text-blue-300 transition-all duration-200 hover:border-blue-400 bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/20"
                  disabled={isScanning}
                >
                  {example}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Trust Indicators */}
        <div className="grid grid-cols-1 gap-8 mt-20 w-full max-w-4xl md:grid-cols-3">
          <div className="p-6 text-center rounded-xl border bg-blue-500/5 border-blue-500/10">
            <div className="flex justify-center items-center mx-auto mb-4 w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-white">94% Accuracy</h3>
            <p className="text-blue-200">Advanced AI models trained on large dataset on scam patterns</p>
          </div>

          <div className="p-6 text-center rounded-xl border bg-blue-500/5 border-blue-500/10">
            <div className="flex justify-center items-center mx-auto mb-4 w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-white">Instant Results</h3>
            <p className="text-blue-200">Get comprehensive scan results in under 3 seconds</p>
          </div>

          <div className="p-6 text-center rounded-xl border bg-blue-500/5 border-blue-500/10">
            <div className="flex justify-center items-center mx-auto mb-4 w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full">
              <Search className="w-6 h-6 text-white" />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-white">Threat Detection</h3>
            <p className="text-blue-200">Identify phishing, malware, and other malicious activities.</p>
          </div>
        </div>
      </main>
    </div>
  )
}
