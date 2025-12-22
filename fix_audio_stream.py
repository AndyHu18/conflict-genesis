#!/usr/bin/env python3
"""修復串流音頻生成邏輯 v2"""

with open('web_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到標記位置
start_marker = "# 3. 逐個生成並立即推送"
end_marker = "'所有片段生成完成'"

start = content.find(start_marker)
end = content.find(end_marker, start)

if start > -1 and end > -1:
    # 找到這一行的結尾
    end = content.find("\n", end) + 1
    
    # 提取要替換的部分
    old_section = content[start:end]
    print(f"找到代碼區塊 ({len(old_section)} 字符)")
    
    # 新代碼
    new_section = '''# 3. 逐個生成並立即推送（邊生成邊播放）
            import time as time_module
            audio_clips = []  # 收集所有片段，用於最後混合 BGM
            failed_parts = []
            
            for i, (part_name, content) in enumerate(parts, 1):
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在生成 {part_name} ({i}/{total_parts})...'})}\\n\\n"
                
                audio_data = None
                last_error = None
                
                # 額外重試機制
                for extra_retry in range(3):
                    try:
                        if extra_retry > 0:
                            yield f"data: {json.dumps({'type': 'status', 'message': f'{part_name} 重試中... (第 {extra_retry + 1} 次)'})}\\n\\n"
                            time_module.sleep(2 * extra_retry)
                        
                        audio_data = generator.text_to_speech_single(content, voice, part_name)
                        break
                        
                    except Exception as e:
                        last_error = e
                        print(f"   ❌ {part_name} 第 {extra_retry + 1} 輪失敗: {e}")
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            break
                
                if audio_data:
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    audio_clips.append(audio_data)
                    
                    yield f"data: {json.dumps({'type': 'audio', 'part': i, 'total': total_parts, 'audio_base64': audio_base64, 'part_name': part_name})}\\n\\n"
                    print(f"   ✅ {part_name} 已推送到前端")
                else:
                    failed_parts.append({'part': part_name, 'error': str(last_error)})
                    yield f"data: {json.dumps({'type': 'part_error', 'part': i, 'error': str(last_error)})}\\n\\n"
            
            # 4. 嘗試混合 BGM
            if audio_clips and len(audio_clips) == total_parts:
                try:
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在混合背景音樂...'})}\\n\\n"
                    stitched_audio = generator.stitch_audio_clips(audio_clips)
                    final_audio, bgm_status = generator._apply_bgm_mixing(stitched_audio, stage2)
                    
                    if bgm_status.get('success'):
                        final_base64 = base64.b64encode(final_audio).decode('utf-8')
                        yield f"data: {json.dumps({'type': 'complete_with_bgm', 'audio_base64': final_base64, 'bgm_method': bgm_status.get('method', 'unknown')})}\\n\\n"
                        print(f"   🎵 BGM 混合成功: {bgm_status.get('method')}")
                    else:
                        yield f"data: {json.dumps({'type': 'bgm_skipped', 'reason': bgm_status.get('error', '未知原因')})}\\n\\n"
                except Exception as bgm_error:
                    print(f"   ⚠️ BGM 混合失敗: {bgm_error}")
                    yield f"data: {json.dumps({'type': 'bgm_error', 'error': str(bgm_error)})}\\n\\n"
            
            # 5. 完成
            yield f"data: {json.dumps({'type': 'complete', 'message': '所有片段生成完成', 'success_count': len(audio_clips), 'fail_count': len(failed_parts)})}\\n\\n"
'''
    
    # 執行替換
    new_content = content[:start] + new_section + content[end:]
    
    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ 修復成功！")
else:
    print(f"❌ 找不到標記: start={start}, end={end}")
