import tiktoken

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    encoding = tiktoken.get_encoding('cl100k_base')
    
    lines = text.split('\n')
    chunks = []
    
    current_chunk_lines = []
    current_tokens = 0
    
    for line in lines:
        line_tokens = len(encoding.encode(line))
        
        # When limit is reached, flush chunk
        if current_tokens + line_tokens > chunk_size and current_chunk_lines:
            chunks.append('\n'.join(current_chunk_lines))
            
            # Start new chunk with overlap
            overlap_tokens = 0
            overlap_lines = []
            for prev_line in reversed(current_chunk_lines):
                prev_line_tokens = len(encoding.encode(prev_line))
                if overlap_tokens + prev_line_tokens > overlap:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_tokens += prev_line_tokens
                
            current_chunk_lines = overlap_lines
            current_tokens = overlap_tokens
            
        current_chunk_lines.append(line)
        current_tokens += line_tokens
        
    if current_chunk_lines:
        chunks.append('\n'.join(current_chunk_lines))
        
    return chunks
