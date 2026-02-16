#!/usr/bin/env python3
"""
Script de prueba para todos los perfiles de optimización
Uso: python test_profiles.py <video_path>
"""

import os
import sys
import time
import json
from modules.pipeline import PipelineSteps
from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

def test_profile(input_path, profile):
    """Prueba un perfil específico y retorna resultados"""
    
    # Generar nombre de salida
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_{profile}{ext}"
    
    print(f"\n{'='*60}")
    print(f"🎬 TESTEANDO PERFIL: {profile.upper()}")
    print(f"{'='*60}")
    
    # Inicializar
    state = StateManager()
    ff = FFmpegHandler(state)
    pipeline = PipelineSteps(ff)
    
    # Obtener duración del video antes de procesar
    duration = ff.get_duration(input_path)
    if duration:
        print(f"⏱️ Duración del video: {duration/60:.1f} minutos")
    
    # Configurar perfil
    pipeline.set_profile(profile)
    
    # Medir tiempo
    start_time = time.time()
    
    # Ejecutar
    success = pipeline.process(input_path, output_path, profile=profile)
    
    elapsed = time.time() - start_time
    
    if success and os.path.exists(output_path):
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        final_size = os.path.getsize(output_path) / (1024 * 1024)
        compression = (1 - final_size/original_size) * 100
        
        result = {
            "profile": profile,
            "success": True,
            "time_seconds": elapsed,
            "time_minutes": elapsed / 60,
            "original_mb": original_size,
            "final_mb": final_size,
            "compression_%": compression,
            "speed_x": (duration / elapsed) if duration and duration > 0 else 0,
            "output": output_path
        }
        
        print(f"\n✅ PERFIL {profile.upper()} COMPLETADO")
        print(f"   Tiempo: {elapsed/60:.1f} minutos")
        print(f"   Original: {original_size:.1f} MB")
        print(f"   Final: {final_size:.1f} MB")
        print(f"   Compresión: {compression:.1f}%")
        if duration:
            print(f"   Velocidad: {duration/elapsed:.2f}x")
        
        return result
    else:
        print(f"\n❌ PERFIL {profile.upper()} FALLÓ")
        return {
            "profile": profile,
            "success": False,
            "time_seconds": elapsed,
            "time_minutes": elapsed / 60,
            "output": None
        }

def main():
    if len(sys.argv) < 2:
        print("Uso: python test_profiles.py <video_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        print(f"❌ No existe el archivo: {input_path}")
        sys.exit(1)
    
    # Perfiles a probar
    profiles = ["ultra_fast", "fast", "balanced", "high_quality", "master"]
    
    results = []
    
    print("\n🔬 INICIANDO BATERÍA DE PRUEBAS")
    print(f"📁 Archivo: {input_path}")
    print(f"📊 Perfiles: {', '.join(profiles)}")
    
    for i, profile in enumerate(profiles, 1):
        print(f"\n--- Prueba {i}/{len(profiles)} ---")
        result = test_profile(input_path, profile)
        results.append(result)
        
        # Pequeña pausa entre pruebas (excepto después de la última)
        if profile != profiles[-1]:
            print("\n⏳ Esperando 5 segundos antes de siguiente perfil...")
            time.sleep(5)
    
    # Mostrar resumen
    print("\n" + "="*70)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*70)
    
    print(f"\n{'PERFIL':<15} {'ESTADO':<8} {'TIEMPO':<12} {'COMPRESIÓN':<12} {'TAMAÑO':<12} {'VELOCIDAD':<10}")
    print("-"*75)
    
    for r in results:
        if r["success"]:
            print(f"{r['profile']:<15} {'✅':<8} {r['time_minutes']:>5.1f} min   {r['compression_%']:>6.1f}%    {r['final_mb']:>6.1f} MB   {r.get('speed_x', 0):>5.2f}x")
        else:
            print(f"{r['profile']:<15} {'❌':<8} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<10}")
    
    # Guardar resultados
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "video": input_path,
            "video_size_mb": os.path.getsize(input_path) / (1024 * 1024),
            "timestamp": time.time(),
            "results": results
        }, f, indent=2)
    
    print(f"\n📝 Resultados guardados en: {results_file}")
    
    # Mostrar recomendación
    print("\n💡 RECOMENDACIÓN:")
    print("   - Para máxima velocidad: ultra_fast o fast")
    print("   - Para mejor balance: balanced")
    print("   - Para máxima calidad: high_quality o master")

if __name__ == "__main__":
    main()