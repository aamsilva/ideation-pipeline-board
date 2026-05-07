#!/usr/bin/env python3
"""
HMN Submarine Monitoring - OTDR/FBG Data Processor
Processamento de dados de sondas óticas (OTDR e Fiber Bragg Grating)
"""
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import csv

class OTDRMeasurement:
    """Dados de medição OTDR (Optical Time Domain Reflectometer)"""
    def __init__(self, distance: np.ndarray, power: np.ndarray, 
                 timestamp: datetime = None, fiber_id: str = "FIBER-001"):
        self.distance = distance  # Array de distâncias (km)
        self.power = power        # Array de potência (dBm)
        self.timestamp = timestamp or datetime.now()
        self.fiber_id = fiber_id
        
    def detect_faults(self, threshold_db: float = -30.0) -> List[Dict]:
        """Deteta falhas baseado na potência"""
        faults = []
        
        # Deteta quedas bruscas de potência
        gradient = np.gradient(self.power)
        fault_indices = np.where(gradient < threshold_db)[0]
        
        for idx in fault_indices:
            if idx < len(self.distance):
                faults.append({
                    'type': 'fiber_break' if self.power[idx] < -40 else 'attenuation',
                    'distance_km': float(self.distance[idx]),
                    'power_dbm': float(self.power[idx]),
                    'gradient_db': float(gradient[idx])
                })
        
        return faults
    
    def calculate_loss(self, start_km: float = 0, end_km: float = 50) -> float:
        """Calcula perda total entre dois pontos"""
        mask = (self.distance >= start_km) & (self.distance <= end_km)
        if not np.any(mask):
            return 0.0
        
        start_power = self.power[np.where(self.distance >= start_km)[0][0]]
        end_power = self.power[np.where(self.distance <= end_km)[0][-1]]
        return abs(start_power - end_power)

class FBGSensor:
    """Sensor FBG (Fiber Bragg Grating) para monitorização de temperatura/strain"""
    def __init__(self, sensor_id: str, wavelength_nm: float, 
                 calibration_factor: float = 1.0):
        self.sensor_id = sensor_id
        self.wavelength_nm = wavelength_nm
        self.calibration_factor = calibration_factor
        self.measurements = []
        
    def add_measurement(self, wavelength_shift: float, timestamp: datetime = None):
        """Adiciona medição baseada no shift de wavelength"""
        measurement = {
            'timestamp': timestamp or datetime.now(),
            'wavelength_shift_nm': wavelength_shift,
            'temperature_c': self._wavelength_to_temperature(wavelength_shift),
            'strain_microstrain': self._wavelength_to_strain(wavelength_shift)
        }
        self.measurements.append(measurement)
        return measurement
    
    def _wavelength_to_temperature(self, shift: float) -> float:
        """Converte shift de wavelength em temperatura (simplificado)"""
        # Coeficiente típico: ~10 pm/°C para FBG
        return shift / 0.01  # nm para °C
    
    def _wavelength_to_strain(self, shift: float) -> float:
        """Converte shift de wavelength em strain (simplificado)"""
        # Coeficiente típico: ~1.2 pm/με para FBG
        return shift / 0.0012  # nm para microstrain

class OpticalProbeProcessor:
    """Processador principal para sondas óticas HMN"""
    
    def __init__(self):
        self.otdr_measurements = []
        self.fbg_sensors = {}
        
    def load_otdr_from_csv(self, filepath: str) -> OTDRMeasurement:
        """Carrega dados OTDR de ficheiro CSV"""
        distance = []
        power = []
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                distance.append(float(row['distance_km']))
                power.append(float(row['power_dbm']))
        
        measurement = OTDRMeasurement(
            distance=np.array(distance),
            power=np.array(power)
        )
        self.otdr_measurements.append(measurement)
        return measurement
    
    def register_fbg_sensor(self, sensor_id: str, wavelength_nm: float):
        """Regista um sensor FBG"""
        self.fbg_sensors[sensor_id] = FBGSensor(sensor_id, wavelength_nm)
        return self.fbg_sensors[sensor_id]
    
    def process_all(self) -> Dict:
        """Processa todos os dados e gera relatório"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'otdr_analysis': [],
            'fbg_analysis': [],
            'health_status': 'healthy'
        }
        
        # Processa OTDR
        for otdr in self.otdr_measurements:
            faults = otdr.detect_faults()
            loss = otdr.calculate_loss()
            
            analysis = {
                'fiber_id': otdr.fiber_id,
                'timestamp': otdr.timestamp.isoformat(),
                'faults_detected': len(faults),
                'faults': faults,
                'total_loss_db': round(loss, 2),
                'health': 'faulty' if faults else 'healthy'
            }
            report['otdr_analysis'].append(analysis)
            
            if faults:
                report['health_status'] = 'degraded'
        
        # Processa FBG
        for sensor_id, sensor in self.fbg_sensors.items():
            if sensor.measurements:
                latest = sensor.measurements[-1]
                report['fbg_analysis'].append({
                    'sensor_id': sensor_id,
                    'latest_temperature_c': round(latest['temperature_c'], 2),
                    'latest_strain_με': round(latest['strain_microstrain'], 2),
                    'total_measurements': len(sensor.measurements)
                })
        
        return report
    
    def export_report(self, filepath: str, format: str = 'json'):
        """Exporta relatório para ficheiro"""
        report = self.process_all()
        
        if format == 'json':
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        elif format == 'csv':
            # Simplificado - exporta apenas OTDR faults
            with open(filepath, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['fiber_id', 'fault_type', 'distance_km', 'power_dbm'])
                for analysis in report['otdr_analysis']:
                    for fault in analysis['faults']:
                        writer.writerow([
                            analysis['fiber_id'],
                            fault['type'],
                            fault['distance_km'],
                            fault['power_dbm']
                        ])

def simulate_hmn_monitoring():
    """Simula monitorização HMN para teste"""
    processor = OpticalProbeProcessor()
    
    # Simula dados OTDR
    distance = np.linspace(0, 100, 1000)  # 0-100km
    power = -10 - (distance * 0.2) + np.random.normal(0, 0.5, 1000)  # Perda linear + ruído
    
    # Adiciona falha em 45km
    fault_idx = np.where(np.abs(distance - 45) < 1)[0]
    power[fault_idx] -= 15  # Queda de 15dB
    
    otdr = OTDRMeasurement(distance, power, fiber_id="HMN-SUB-001")
    processor.otdr_measurements.append(otdr)
    
    # Regista sensores FBG
    fbg1 = processor.register_fbg_sensor("FBG-001", 1550.0)
    fbg1.add_measurement(0.05)  # 5nm shift
    fbg1.add_measurement(0.06)
    
    fbg2 = processor.register_fbg_sensor("FBG-002", 1552.0)
    fbg2.add_measurement(0.03)
    
    # Gera relatório
    return processor.process_all()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--simulate':
        print("Simulando monitorização HMN...")
        report = simulate_hmn_monitoring()
        print(json.dumps(report, indent=2, default=str))
    else:
        print("HMN Optical Probe Data Processor")
        print("Uso: python optical_processor.py --simulate")
        print("Ou use a classe OpticalProbeProcessor no seu código")
