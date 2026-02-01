import React, { useState, useEffect, useRef } from 'react';
import { Search, Send, CheckCircle, AlertCircle, Clock, X, Loader2, Info, Code, FileText, TrendingUp, TrendingDown, DollarSign, PieChart, ArrowRight, Newspaper, BarChart3, AlertTriangle, Sparkles, Brain } from 'lucide-react';

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Mock Portfolio Data (unchanged)
const MOCK_PORTFOLIO = {
  accounts: [
    { id: 'ACC001', name: 'Investment Account', type: 'Brokerage', balance: 1250000.00, currency: 'USD', performance: 12.5 },
    { id: 'ACC002', name: 'Retirement Account', type: '401(k)', balance: 850000.00, currency: 'USD', performance: 8.3 },
    { id: 'ACC003', name: 'Trading Account', type: 'Active Trading', balance: 450000.00, currency: 'USD', performance: -2.1 }
  ],
  holdings: [
    { symbol: 'AAPL', name: 'Apple Inc.', quantity: 2500, avgPrice: 150.00, currentPrice: 178.50, market: 'NASDAQ', currency: 'USD' },
    { symbol: 'MSFT', name: 'Microsoft Corporation', quantity: 1200, avgPrice: 320.00, currentPrice: 378.91, market: 'NASDAQ', currency: 'USD' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.', quantity: 800, avgPrice: 125.00, currentPrice: 140.25, market: 'NASDAQ', currency: 'USD' },
    { symbol: 'TSLA', name: 'Tesla Inc.', quantity: 500, avgPrice: 200.00, currentPrice: 242.84, market: 'NASDAQ', currency: 'USD' },
    { symbol: 'NOVN', name: 'Novartis AG', quantity: 3000, avgPrice: 85.00, currentPrice: 95.20, market: 'SIX', currency: 'CHF' },
    { symbol: 'NESN', name: 'Nestlé S.A.', quantity: 2000, avgPrice: 92.00, currentPrice: 87.45, market: 'SIX', currency: 'CHF' }
  ],
  totalValue: 2550000.00,
  todayChange: 15420.00,
  todayChangePercent: 0.61
};

const SECURITIES = [
  { symbol: 'AAPL', market: 'NASDAQ', currency: 'USD', name: 'Apple Inc.', price: 178.50 },
  { symbol: 'GOOGL', market: 'NASDAQ', currency: 'USD', name: 'Alphabet Inc.', price: 140.25 },
  { symbol: 'MSFT', market: 'NASDAQ', currency: 'USD', name: 'Microsoft Corporation', price: 378.91 },
  { symbol: 'TSLA', market: 'NASDAQ', currency: 'USD', name: 'Tesla Inc.', price: 242.84 },
  { symbol: 'NOVN', market: 'SIX', currency: 'CHF', name: 'Novartis AG', price: 95.20 },
  { symbol: 'NESN', market: 'SIX', currency: 'CHF', name: 'Nestlé S.A.', price: 87.45 },
];

const MARKET_STATUS = {
  NASDAQ: { open: false, nextOpen: '2026-01-31 09:30' },
  SIX: { open: false, nextOpen: '2026-01-31 09:00' }
};

const WORKFLOW_STAGES = [
  { id: 'entry', label: 'Order Entry', icon: '📝' },
  { id: 'validation', label: 'AI Validation', icon: '✓' },
  { id: 'submission', label: 'Submission', icon: '📤' },
  { id: 'market', label: 'Market Order', icon: '📊' },
  { id: 'execution', label: 'Execution', icon: '✅' }
];

const ALGO_SUGGESTIONS = [
  { id: 'vwap', name: 'VWAP', description: 'Volume Weighted Average Price', useCase: 'Best for large orders to minimize market impact' },
  { id: 'twap', name: 'TWAP', description: 'Time Weighted Average Price', useCase: 'Ideal for consistent execution' },
  { id: 'pov', name: 'POV', description: 'Percentage of Volume', useCase: 'Good for following market rhythm' },
  { id: 'moc', name: 'MOC', description: 'Market on Close', useCase: 'Execute at closing auction' }
];

// ============================================================================
// AGENT LIGHTNING INTEGRATION - API Service
// ============================================================================

const apiService = {
  // Generate unique interaction ID for tracking
  generateInteractionId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  },

  async parseOrder(text) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/parse-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!response.ok) throw new Error('API error');
      return await response.json();
    } catch (error) {
      console.error('Parse order error:', error);
      return this.fallbackParseOrder(text);
    }
  },

  async parseTraderText(text, orderContext) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/parse-trader-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, context: orderContext })
      });
      if (!response.ok) throw new Error('API error');
      return await response.json();
    } catch (error) {
      console.error('Parse trader text error:', error);
      return this.fallbackTraderText(text);
    }
  },

  async getSmartSuggestion(orderDetails, interactionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/smart-suggestion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...orderDetails,
          interaction_id: interactionId  // Track for Agent Lightning
        })
      });
      if (!response.ok) throw new Error('API error');
      return await response.json();
    } catch (error) {
      console.error('Smart suggestion error:', error);
      return this.fallbackSmartSuggestion(orderDetails);
    }
  },

  async getAutocomplete(text) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/autocomplete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!response.ok) throw new Error('API error');
      return await response.json();
    } catch (error) {
      console.error('Autocomplete error:', error);
      return [];
    }
  },

  // ============================================================================
  // NEW: Capture correction for Agent Lightning RL training
  // ============================================================================
  async captureCorrection(interactionId, aiSuggestion, userChoice, orderDetails) {
    try {
      console.log('📊 Capturing correction for RL training:', {
        interactionId,
        ai: aiSuggestion.suggested_strategy,
        user: userChoice
      });

      const response = await fetch(`${API_BASE_URL}/api/correction/strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          interaction_id: interactionId,
          security: orderDetails.security,
          quantity: orderDetails.quantity,
          timeInForce: orderDetails.timeInForce,
          ai_strategy: aiSuggestion.suggested_strategy,
          ai_reasoning: aiSuggestion.reasoning,
          user_strategy: userChoice,
          user_reason: 'User manually selected different strategy'
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ Correction captured for Agent Lightning:', result);
        return result;
      }
    } catch (error) {
      console.error('❌ Error capturing correction:', error);
    }
    return null;
  },

  // Fallback methods (unchanged)
  fallbackParseOrder(text) {
    const lower = text.toLowerCase();
    const security = SECURITIES.find(s => lower.includes(s.symbol.toLowerCase()));
    const qtyMatch = text.match(/(\d+)/);
    return {
      security,
      quantity: qtyMatch ? parseInt(qtyMatch[1]) : 100,
      time_in_force: lower.includes('gtc') ? 'GTC' : 'DAY',
      contact_method: 'phone',
      price: null
    };
  },

  fallbackTraderText(text) {
    const lower = text.toLowerCase();
    if (lower.includes('vwap')) {
      return {
        structured: 'VWAP Market Close [16:00]',
        backend_format: 'VWAP|END=16:00|START=09:30',
        description: 'Execute throughout the day to match volume-weighted average price.',
        algo: 'vwap',
        confidence: 0.9,
        reasoning: 'VWAP detected in trader text',
        parameters: {}
      };
    }
    return {
      structured: text,
      backend_format: `CUSTOM|${text}`,
      description: 'Custom execution',
      algo: null,
      confidence: 0.5,
      reasoning: 'No specific algorithm detected',
      parameters: {}
    };
  },

  fallbackSmartSuggestion(orderDetails) {
    return {
      suggested_strategy: 'VWAP',
      reasoning: 'Default strategy recommendation',
      warnings: [],
      market_impact_risk: 'LOW',
      behavioral_notes: 'Standard execution approach'
    };
  }
};

export default function UBSIntegratedOMS() {
  const [currentView, setCurrentView] = useState('portfolio');
  const [showGeneiChat, setShowGeneiChat] = useState(false);
  const [geneiInput, setGeneiInput] = useState('');
  const [chatHistory, setChatHistory] = useState([
    {
      type: 'assistant',
      message: 'Hello! I\'m Trade Assistant with Agent Lightning RL. I learn from your corrections to improve over time.\n\nToday is January 30, 2026.',
      timestamp: new Date().toISOString()
    }
  ]);
  const [backendStatus, setBackendStatus] = useState('checking');

  // Order Entry State
  const [orderForm, setOrderForm] = useState({
    security: null,
    contactMethod: 'phone',
    quantity: '',
    price: '',
    timeInForce: 'DAY',
    gtdDate: '',
    traderText: ''
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [showSecurityDropdown, setShowSecurityDropdown] = useState(false);
  const [filteredSecurities, setFilteredSecurities] = useState([]);

  // AI State
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [traderTextParsed, setTraderTextParsed] = useState(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState('');
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const [workflowStage, setWorkflowStage] = useState('entry');
  const [validationStatus, setValidationStatus] = useState(null);
  const [selectedAlgo, setSelectedAlgo] = useState(null);
  const [userProvidedTraderText, setUserProvidedTraderText] = useState(false);

  // ============================================================================
  // NEW: Agent Lightning state
  // ============================================================================
  const [currentInteractionId, setCurrentInteractionId] = useState(null);
  const [originalAISuggestion, setOriginalAISuggestion] = useState(null);
  const [correctionCaptured, setCorrectionCaptured] = useState(false);
  const [showRLNotification, setShowRLNotification] = useState(false);

  const chatEndRef = useRef(null);
  const debounceTimer = useRef(null);
  const autocompleteTimer = useRef(null);
  const traderTextRef = useRef(null);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/`);
        const data = await response.json();
        setBackendStatus(response.ok ? 'connected' : 'disconnected');
        
        // Check if Agent Lightning is available
        if (data.features?.agent_lightning) {
          console.log('🧠 Agent Lightning enabled on backend');
        }
      } catch {
        setBackendStatus('disconnected');
      }
    };
    checkBackend();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Security search (unchanged)
  useEffect(() => {
    if (searchTerm) {
      const filtered = SECURITIES.filter(s =>
        s.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredSecurities(filtered);
      setShowSecurityDropdown(true);
    } else {
      setFilteredSecurities([]);
      setShowSecurityDropdown(false);
    }
  }, [searchTerm]);

  // ============================================================================
  // MODIFIED: Smart AI suggestion with Agent Lightning tracking
  // ============================================================================
  useEffect(() => {
    if (orderForm.security && orderForm.quantity && !userProvidedTraderText) {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);

      debounceTimer.current = setTimeout(async () => {
        setIsLoadingAI(true);
        
        // Generate new interaction ID for this suggestion
        const interactionId = apiService.generateInteractionId();
        setCurrentInteractionId(interactionId);
        setCorrectionCaptured(false);
        
        console.log('🧠 Calling smart suggestion with Agent Lightning tracking...');
        const suggestion = await apiService.getSmartSuggestion({
          security: orderForm.security.symbol,
          quantity: parseInt(orderForm.quantity),
          timeInForce: orderForm.timeInForce
        }, interactionId);

        console.log('✅ Smart suggestion received:', suggestion);
        setAiSuggestion(suggestion);
        setOriginalAISuggestion(suggestion); // Store for correction comparison

        // Auto-generate trader text from AI suggestion
        if (suggestion.suggested_strategy && !orderForm.traderText) {
          const autoText = `${suggestion.suggested_strategy} execution`;
          setOrderForm(prev => ({ ...prev, traderText: autoText }));

          // Parse it
          const parsed = await apiService.parseTraderText(autoText, {
            symbol: orderForm.security.symbol,
            quantity: orderForm.quantity
          });
          setTraderTextParsed(parsed);
        }

        setIsLoadingAI(false);
      }, 1000);
    }
  }, [orderForm.security, orderForm.quantity, orderForm.timeInForce, userProvidedTraderText]);

  // Parse trader text when user manually types (unchanged)
  useEffect(() => {
    if (orderForm.traderText && userProvidedTraderText) {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);

      debounceTimer.current = setTimeout(async () => {
        setIsLoadingAI(true);
        console.log('Parsing trader text:', orderForm.traderText);
        const parsed = await apiService.parseTraderText(orderForm.traderText, {
          symbol: orderForm.security?.symbol,
          quantity: orderForm.quantity
        });
        console.log('Trader text parsed:', parsed);
        setTraderTextParsed(parsed);
        setIsLoadingAI(false);
      }, 500);
    }
  }, [orderForm.traderText, userProvidedTraderText, orderForm.security, orderForm.quantity]);

  // Autocomplete (unchanged)
  useEffect(() => {
    if (
      orderForm.traderText &&
      orderForm.traderText.length >= 2 &&
      userProvidedTraderText
    ) {
      if (autocompleteTimer.current) clearTimeout(autocompleteTimer.current);

      autocompleteTimer.current = setTimeout(async () => {
        const suggestions = await apiService.getAutocomplete(orderForm.traderText);
        if (suggestions?.length > 0) {
          let best = suggestions[0];
          const matching = suggestions.find(s =>
            s.toLowerCase().startsWith(orderForm.traderText.toLowerCase())
          );
          if (matching) best = matching;
          setSelectedSuggestion(best);
        } else {
          setSelectedSuggestion('');
        }
      }, 350);

      return () => {
        if (autocompleteTimer.current) clearTimeout(autocompleteTimer.current);
      };
    } else {
      setSelectedSuggestion('');
    }
  }, [orderForm.traderText, userProvidedTraderText]);

  const handleSecuritySelect = (security) => {
    setOrderForm({
      ...orderForm,
      security,
      price: security.price.toString()
    });
    setSearchTerm('');
    setShowSecurityDropdown(false);
  };

  const handleTraderTextChange = (text) => {
    setUserProvidedTraderText(text.length > 0);
    setOrderForm({ ...orderForm, traderText: text });
  };

  const getGhostText = () => {
    if (!selectedSuggestion || !orderForm.traderText) return '';
    const input = orderForm.traderText;
    const suggestion = selectedSuggestion;
    if (suggestion.toLowerCase().startsWith(input.toLowerCase())) {
      return suggestion.slice(input.length);
    }
    return '';
  };
  
  const handleTraderTextKeyDown = (e) => {
    if (e.key === 'Tab' && selectedSuggestion) {
      e.preventDefault();
      setOrderForm(prev => ({ ...prev, traderText: selectedSuggestion }));
      setSelectedSuggestion('');
    } else if (e.key === 'Escape') {
      setSelectedSuggestion('');
    }
  };

  const handleGeneiSubmit = async () => {
    if (!geneiInput.trim()) return;

    const userMessage = { 
      type: 'user', 
      message: geneiInput, 
      timestamp: new Date().toISOString() 
    };
    setChatHistory(prev => [...prev, userMessage]);

    const input = geneiInput;
    setGeneiInput('');
    const lower = input.toLowerCase();

    // Trading intent
    if (
      lower.match(/\b(buy|sell|trade|order)\b/) ||
      input.includes("Client:") ||
      input.includes("Advisor:") ||
      input.includes("Execution Advisor:")
    ) {
      setChatHistory(prev => [...prev, {
        type: 'assistant',
        message: '🔄 Parsing order with MCP + Agent Lightning...',
        timestamp: new Date().toISOString()
      }]);

      const parsed = await apiService.parseOrder(input);

      if (parsed.security) {
        let traderTextValue = '';
        if (parsed.requested_strategy) {
          traderTextValue = `${parsed.requested_strategy} execution`;
        } else if (input.trim()) {
          const traderParsed = await apiService.parseTraderText(input, {
            symbol: parsed.security?.symbol,
            quantity: parsed.quantity
          });
          if (traderParsed?.algo) {
            traderTextValue = traderParsed.structured || 
                             `${traderParsed.algo.toUpperCase()} execution`;
          }
        }

        setOrderForm({
          security: parsed.security,
          quantity: parsed.quantity?.toString() || '',
          price: parsed.price?.toString() || parsed.security.price.toString(),
          timeInForce: parsed.time_in_force || 'DAY',
          contactMethod: parsed.contact_method || 'phone',
          traderText: traderTextValue,
          gtdDate: ''
        });

        setChatHistory(prev => [...prev, {
          type: 'assistant',
          message: `✅ Order parsed!\n\n` +
                   `• Security: ${parsed.security.symbol}\n` +
                   `• Quantity: ${parsed.quantity}\n` +
                   `• Strategy: ${traderTextValue || 'AI will suggest'}\n` +
                   `\n🧠 Agent Lightning will track corrections for RL training.`,
          timestamp: new Date().toISOString()
        }]);

        setTimeout(() => {
          setCurrentView('orderEntry');
          setShowGeneiChat(false);
        }, 1500);
      }
    }
    // Portfolio summary
    else if (lower.match(/\b(portfolio|holdings|summary)\b/)) {
      const summary = `📊 Portfolio Summary:\n\n💰 Total Value: $${MOCK_PORTFOLIO.totalValue.toLocaleString()}\n📈 Today: +$${MOCK_PORTFOLIO.todayChange.toLocaleString()} (+${MOCK_PORTFOLIO.todayChangePercent}%)\n\n📁 Holdings: ${MOCK_PORTFOLIO.holdings.length} securities\n💼 Accounts: ${MOCK_PORTFOLIO.accounts.length} accounts`;
      setChatHistory(prev => [...prev, { type: 'assistant', message: summary, timestamp: new Date().toISOString() }]);
    }
    // General
    else {
      setChatHistory(prev => [...prev, {
        type: 'assistant',
        message: 'I can help with:\n\n📊 Portfolio analysis\n💼 Place trades with RL-powered suggestions\n🧠 I learn from your corrections!\n\nWhat would you like to do?',
        timestamp: new Date().toISOString()
      }]);
    }
  };

  const validateOrder = () => {
    setWorkflowStage('validation');
    setValidationStatus(null);
    if (!orderForm.security) {
      setValidationStatus({ type: 'error', message: 'Please select a security' });
      return;
    }
    if (!orderForm.quantity || parseInt(orderForm.quantity) <= 0) {
      setValidationStatus({ type: 'error', message: 'Please enter valid quantity' });
      return;
    }
    const marketStatus = MARKET_STATUS[orderForm.security.market];
    if (orderForm.timeInForce === 'DAY' && !marketStatus.open) {
      setValidationStatus({ type: 'warning', message: 'Market closed - DAY order cannot be placed' });
      setAiSuggestion({
        action: 'convert_to_gtd',
        message: `${orderForm.security.market} market is closed. Convert to GTD?`,
        nextDate: marketStatus.nextOpen
      });
      return;
    }
    setValidationStatus({ type: 'success', message: 'Validation successful' });

    setTimeout(() => {
      setWorkflowStage('market');

      if (traderTextParsed && traderTextParsed.algo) {
        const algo = ALGO_SUGGESTIONS.find(a => a.id === traderTextParsed.algo);
        setAiSuggestion({
          action: 'confirm_algo',
          message: `Detected ${algo?.name} strategy. Proceed?`,
          algo: traderTextParsed.algo
        });

        setChatHistory(prev => [...prev, {
          type: 'assistant',
          message: `🤖 AI Analysis:\n\n📊 "${traderTextParsed.structured}"\n💻 ${traderTextParsed.backend_format}\n\nConfidence: ${(traderTextParsed.confidence * 100).toFixed(0)}%\n\nProceed?`,
          timestamp: new Date().toISOString()
        }]);
      } else {
        executeOrder();
      }
    }, 1000);
  };

  // ============================================================================
  // MODIFIED: Execute order with correction capture
  // ============================================================================
  const executeOrder = async () => {
    setWorkflowStage('execution');
    setValidationStatus({ type: 'success', message: 'Order executed' });

    // Capture correction if user chose different strategy than AI suggested
    if (originalAISuggestion && traderTextParsed && !correctionCaptured) {
      const aiStrategy = originalAISuggestion.suggested_strategy?.toUpperCase();
      const userStrategy = traderTextParsed.algo?.toUpperCase();
      
      if (aiStrategy && userStrategy && aiStrategy !== userStrategy) {
        console.log(`🧠 User chose ${userStrategy} instead of AI's ${aiStrategy} - capturing correction`);
        
        await apiService.captureCorrection(
          currentInteractionId,
          originalAISuggestion,
          userStrategy,
          {
            security: orderForm.security.symbol,
            quantity: parseInt(orderForm.quantity),
            timeInForce: orderForm.timeInForce
          }
        );
        
        setCorrectionCaptured(true);
        setShowRLNotification(true);
        
        // Hide notification after 5 seconds
        setTimeout(() => setShowRLNotification(false), 5000);
      }
    }

    const summary = `
═══════════════════════════════════
✅ ORDER EXECUTED
═══════════════════════════════════
Order ID: OMS-${Date.now().toString().slice(-8)}
Time: ${new Date().toLocaleTimeString()}
Date: January 30, 2026

📊 SECURITY
${orderForm.security?.symbol} - ${orderForm.security?.name}
Market: ${orderForm.security?.market}
Price: ${orderForm.security?.currency} ${orderForm.security?.price}

📈 ORDER DETAILS
Quantity: ${orderForm.quantity} shares
Type: ${orderForm.price ? 'Limit' : 'Market'}
${orderForm.price ? `Limit Price: $${orderForm.price}` : ''}
Time in Force: ${orderForm.timeInForce}

${traderTextParsed ? `🤖 AI EXECUTION STRATEGY
Algorithm: ${traderTextParsed.algo?.toUpperCase() || 'CUSTOM'}
Strategy: ${traderTextParsed.structured}
Backend: ${traderTextParsed.backend_format}
Confidence: ${(traderTextParsed.confidence * 100).toFixed(0)}%
` : ''}
${correctionCaptured ? `
🧠 AGENT LIGHTNING
Your correction was captured for RL training!
This helps improve future suggestions.
` : ''}
═══════════════════════════════════
    `;

    setChatHistory(prev => [...prev, {
      type: 'summary',
      message: summary,
      timestamp: new Date().toISOString()
    }]);
  };

  const handleAISuggestion = (accept) => {
    if (aiSuggestion?.action === 'convert_to_gtd') {
      if (accept) {
        setOrderForm(prev => ({
          ...prev,
          timeInForce: 'GTD',
          gtdDate: aiSuggestion.nextDate.split(' ')[0]
        }));
        setAiSuggestion(null);
        setWorkflowStage('entry');
      } else {
        setAiSuggestion(null);
        setWorkflowStage('entry');
      }
    } else if (aiSuggestion?.action === 'confirm_algo') {
      if (accept) {
        setSelectedAlgo(aiSuggestion.algo);
        setAiSuggestion(null);
        executeOrder();
      } else {
        setAiSuggestion({ action: 'select_algo', message: 'Choose an algorithm:' });
      }
    }
  };

  // ============================================================================
  // MODIFIED: Algorithm selection with correction capture
  // ============================================================================
  const handleAlgoSelection = async (algoId) => {
    setSelectedAlgo(algoId);
    
    // Capture correction if user manually selected different algo
    if (originalAISuggestion && !correctionCaptured) {
      const aiStrategy = originalAISuggestion.suggested_strategy?.toUpperCase();
      const userStrategy = algoId.toUpperCase();
      
      if (aiStrategy && aiStrategy !== userStrategy) {
        console.log(`🧠 Manual algo selection: ${userStrategy} vs AI's ${aiStrategy}`);
        
        await apiService.captureCorrection(
          currentInteractionId,
          originalAISuggestion,
          userStrategy,
          {
            security: orderForm.security.symbol,
            quantity: parseInt(orderForm.quantity),
            timeInForce: orderForm.timeInForce
          }
        );
        
        setCorrectionCaptured(true);
        setShowRLNotification(true);
        setTimeout(() => setShowRLNotification(false), 5000);
      }
    }
    
    setAiSuggestion(null);
    executeOrder();
  };

  const calculateGainLoss = (holding) => {
    const totalCost = holding.quantity * holding.avgPrice;
    const currentValue = holding.quantity * holding.currentPrice;
    const gainLoss = currentValue - totalCost;
    const gainLossPercent = ((currentValue - totalCost) / totalCost) * 100;
    return { gainLoss, gainLossPercent, currentValue };
  };

  // ==================== RENDER ====================
  if (currentView === 'orderEntry') {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* RL Notification Banner */}
        {showRLNotification && (
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-3 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-3">
              <Brain className="animate-pulse" size={24} />
              <div>
                <div className="font-semibold">Agent Lightning: Correction Captured!</div>
                <div className="text-sm text-purple-100">Your feedback will improve future suggestions through RL training</div>
              </div>
            </div>
            <button onClick={() => setShowRLNotification(false)} className="text-white hover:bg-white/20 rounded p-1">
              <X size={20} />
            </button>
          </div>
        )}

        {/* Header */}
        <div className="bg-white border-b-4 border-red-600 shadow-sm">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-red-600 font-bold text-3xl">UBS</div>
              <div className="h-8 w-px bg-gray-300"></div>
              <div className="text-gray-700 font-medium">OMS + Agent Lightning</div>
              <button
                onClick={() => setCurrentView('portfolio')}
                className="ml-4 px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg"
              >
                ← Portfolio
              </button>
              <div className={`ml-3 px-2 py-1 rounded text-xs font-medium ${
                backendStatus === 'connected' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
              }`}>
                {backendStatus === 'connected' ? '● MCP + AGL' : '● Demo Mode'}
              </div>
            </div>
            <button
              onClick={() => setShowGeneiChat(!showGeneiChat)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium ${
                showGeneiChat ? 'bg-red-600 text-white' : 'bg-white text-gray-700 border border-gray-300 hover:border-red-600'
              }`}
            >
              <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center text-white font-bold">T</div>
              <span>Trade Assistant</span>
            </button>
          </div>
        </div>

        {/* Main content - keeping your existing layout but can continue in next message due to length */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-auto">
            <div className="max-w-7xl mx-auto px-6 py-8">
              {/* Workflow stages - unchanged from your code */}
              <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">Order Workflow</h2>
                <div className="flex items-center justify-between">
                  {WORKFLOW_STAGES.map((stage, idx) => {
                    const currentIdx = WORKFLOW_STAGES.findIndex(s => s.id === workflowStage);
                    const isActive = idx === currentIdx;
                    const isComplete = idx < currentIdx;
                    return (
                      <React.Fragment key={stage.id}>
                        <div className="flex flex-col items-center gap-2">
                          <div className={`w-12 h-12 rounded-full flex items-center justify-center text-xl ${
                            isActive ? 'bg-red-600 text-white ring-4 ring-red-100' :
                            isComplete ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-500'
                          }`}>
                            {stage.icon}
                          </div>
                          <div className={`text-xs font-medium text-center ${
                            isActive ? 'text-red-600' : isComplete ? 'text-green-600' : 'text-gray-500'
                          }`}>
                            {stage.label}
                          </div>
                        </div>
                        {idx < WORKFLOW_STAGES.length - 1 && (
                          <div className={`flex-1 h-1 mx-4 ${idx < currentIdx ? 'bg-green-600' : 'bg-gray-200'}`}></div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              </div>

              {/* Rest of your order entry form - keeping all existing code... */}
              {/* Due to length limits, the rest matches your original code exactly */}
              {/* The key changes are in: */}
              {/* 1. apiService methods (added correction capture) */}
              {/* 2. executeOrder (captures corrections) */}
              {/* 3. handleAlgoSelection (captures corrections) */}
              {/* 4. Added RL notification banner */}
              {/* 5. Updated status indicators */}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Portfolio view - unchanged from your original code
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Your existing portfolio code */}
    </div>
  );
}
