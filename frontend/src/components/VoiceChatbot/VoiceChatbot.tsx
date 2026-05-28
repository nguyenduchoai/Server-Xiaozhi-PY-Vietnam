import { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Send, Pause, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import './VoiceChatbot.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  slides?: Slide[];
}

interface Slide {
  id: string;
  imageUrl: string;
  title: string;
  description?: string;
}

interface VoiceChatbotProps {
  apiEndpoint?: string;
  className?: string;
}

export function VoiceChatbot({ apiEndpoint = '/api/v1/chat', className = '' }: VoiceChatbotProps) {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  const startListening = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      
      const chunks: Blob[] = [];
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/webm' });
        await processAudio(audioBlob);
      };
      
      mediaRecorder.start();
      setIsListening(true);
      setError(null);
      
      const updateAudioLevel = () => {
        if (analyserRef.current) {
          const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
          setAudioLevel(average / 255);
        }
        animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
      };
      updateAudioLevel();
      
    } catch (err) {
      setError('Không thể truy cập microphone. Vui lòng kiểm tra quyền truy cập.');
      console.error('Microphone access error:', err);
    }
  }, []);
  
  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    setIsListening(false);
    setAudioLevel(0);
    
    mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
  }, []);
  
  const processAudio = async (audioBlob: Blob) => {
    setIsProcessing(true);
    const startTime = Date.now();
    
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('mode', 'voice');
      
      const response = await fetch(`${apiEndpoint}/voice`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Lỗi khi xử lý yêu cầu');
      }
      
      const data = await response.json();
      const processingTime = Date.now() - startTime;
      
      if (processingTime > 3000) {
        console.warn(`Xử lý vượt quá 3 giây: ${processingTime}ms`);
      }
      
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: data.transcript || 'Đã ghi nhận yêu cầu',
        timestamp: new Date(),
      };
      
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        slides: data.slides || [],
      };
      
      setMessages(prev => [...prev, userMessage, assistantMessage]);
      
      if (data.audioUrl) {
        playAudioResponse(data.audioUrl);
      }
      
    } catch (err) {
      setError('Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại.');
      console.error('Processing error:', err);
    } finally {
      setIsProcessing(false);
    }
  };
  
  const playAudioResponse = (url: string) => {
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.onended = () => setIsPlaying(false);
    audio.play();
    setIsPlaying(true);
  };
  
  const togglePlayback = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };
  
  const nextSlide = () => {
    const currentMessage = messages[messages.length - 1];
    if (currentMessage?.slides && currentSlideIndex < currentMessage.slides.length - 1) {
      setCurrentSlideIndex(prev => prev + 1);
    }
  };
  
  const prevSlide = () => {
    if (currentSlideIndex > 0) {
      setCurrentSlideIndex(prev => prev - 1);
    }
  };
  
  const handleTextSubmit = async (text: string) => {
    if (!text.trim()) return;
    
    setIsProcessing(true);
    const startTime = Date.now();
    
    try {
      const response = await fetch(`${apiEndpoint}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, mode: 'text' }),
      });
      
      const processingTime = Date.now() - startTime;
      if (processingTime > 3000) {
        console.warn(`Xử lý vượt quá 3 giây: ${processingTime}ms`);
      }
      
      if (!response.ok) throw new Error('Lỗi khi xử lý yêu cầu');
      
      const data = await response.json();
      
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: new Date(),
      };
      
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        slides: data.slides || [],
      };
      
      setMessages(prev => [...prev, userMessage, assistantMessage]);
      
      if (data.audioUrl) {
        playAudioResponse(data.audioUrl);
      }
      
    } catch (err) {
      setError('Đã xảy ra lỗi. Vui lòng thử lại.');
    } finally {
      setIsProcessing(false);
    }
  };
  
  const currentSlides = messages[messages.length - 1]?.slides || [];
  const currentSlide = currentSlides[currentSlideIndex];
  
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (mediaRecorderRef.current?.state !== 'inactive') {
        mediaRecorderRef.current?.stop();
      }
    };
  }, []);
  
  return (
    <div className={`voice-chatbot ${className}`}>
      <div className="chat-container">
        <header className="chat-header">
          <h2>Voice Assistant</h2>
          <span className="status-indicator">
            {isProcessing ? 'Đang xử lý...' : 'Sẵn sàng'}
          </span>
        </header>
        
        <div className="messages-container">
          {messages.length === 0 && (
            <div className="empty-state">
              <Mic size={48} />
              <p>Nhấn microphone và bắt đầu nói</p>
              <p className="hint">Hoặc nhập tin nhắn bên dưới</p>
            </div>
          )}
          
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-content">
                {message.content}
              </div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
        
        {currentSlides.length > 0 && (
          <div className="slideshow-container">
            <div className="slide-content">
              {currentSlide ? (
                <>
                  <img 
                    src={currentSlide.imageUrl} 
                    alt={currentSlide.title}
                    className="slide-image"
                  />
                  <div className="slide-info">
                    <h3>{currentSlide.title}</h3>
                    {currentSlide.description && (
                      <p>{currentSlide.description}</p>
                    )}
                  </div>
                </>
              ) : (
                <div className="no-slide">Không có hình ảnh</div>
              )}
            </div>
            
            <div className="slideshow-controls">
              <button 
                onClick={prevSlide}
                disabled={currentSlideIndex === 0}
                className="slide-btn"
              >
                <ChevronLeft />
              </button>
              <span className="slide-counter">
                {currentSlideIndex + 1} / {currentSlides.length}
              </span>
              <button 
                onClick={nextSlide}
                disabled={currentSlideIndex >= currentSlides.length - 1}
                className="slide-btn"
              >
                <ChevronRight />
              </button>
            </div>
          </div>
        )}
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        <div className="input-controls">
          <button
            onClick={isListening ? stopListening : startListening}
            className={`mic-button ${isListening ? 'listening' : ''}`}
            disabled={isProcessing}
            aria-label={isListening ? 'Dừng ghi âm' : 'Bắt đầu ghi âm'}
            data-testid="mic-button"
          >
            {isListening ? (
              <MicOff size={24} aria-hidden="true" />
            ) : (
              <Mic size={24} aria-hidden="true" />
            )}
            {isListening && (
              <div 
                className="audio-level"
                style={{ width: `${audioLevel * 100}%` }}
              />
            )}
          </button>
          
          {isProcessing && (
            <div className="processing-indicator">
              <Loader2 className="spinner" size={20} />
              <span>Đang xử lý...</span>
            </div>
          )}
          
          {isPlaying && (
            <button onClick={togglePlayback} className="playback-btn">
              <Pause size={20} />
            </button>
          )}
          
          <TextInput onSubmit={handleTextSubmit} disabled={isProcessing} />
        </div>
      </div>
    </div>
  );
}

interface TextInputProps {
  onSubmit: (text: string) => void;
  disabled?: boolean;
}

function TextInput({ onSubmit, disabled }: TextInputProps) {
  const [text, setText] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim() && !disabled) {
      onSubmit(text);
      setText('');
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="text-input-form">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Nhập tin nhắn..."
        disabled={disabled}
        className="text-input"
      />
      <button type="submit" disabled={disabled || !text.trim()} className="send-btn">
        <Send size={20} />
      </button>
    </form>
  );
}

export default VoiceChatbot;
