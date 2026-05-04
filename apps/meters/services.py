# apps/meters/services.py
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import WaterMeter, MeterReading


# ──────────────────────────────────────────────
# Configurações de anomalia (podem virar settings)
# ──────────────────────────────────────────────
ANOMALY_MULTIPLIER = 3.0      # consumo > 3× a média histórica → anomalia
ANOMALY_MIN_READINGS = 3      # mínimo de leituras anteriores para calcular média
ANOMALY_ZERO_ALERT = True     # consumo zero após leituras anteriores → alerta


class ReadingValidationError(Exception):
    """Erro de validação de negócio (não HTTP)."""
    pass


class MeterReadingService:
    """
    Camada de serviço para registro e validação de leituras.
    Mantém toda a lógica de negócio fora das views e serializers.
    """

    # ──────────────────────────────────────────
    # Ponto de entrada principal
    # ──────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def register_reading(
        cls,
        meter: WaterMeter,
        reading_value: Decimal,
        reading_date=None,
        reader=None,
        image_evidence=None,
    ) -> MeterReading:
        """
        Registra uma nova leitura validando todas as regras de negócio.
        Retorna a MeterReading criada (com flag is_anomaly preenchida).
        """
        if reading_date is None:
            reading_date = timezone.now()

        # 1. Validações
        cls._validate_meter_active(meter)
        cls._validate_reading_value(meter, reading_value)
        cls._validate_reading_date(meter, reading_date)

        # 2. Criar leitura
        reading = MeterReading.objects.create(
            meter=meter,
            company=meter.company,
            reader=reader,
            reading_value=reading_value,
            reading_date=reading_date,
            image_evidence=image_evidence,
        )

        # 3. Detecção de anomalia (após criar para ter ID)
        anomaly = cls.detect_anomaly(reading)
        if anomaly['is_anomaly']:
            reading.anomaly_flag = True
            reading.anomaly_reason = anomaly['reason']
            reading.save(update_fields=['anomaly_flag', 'anomaly_reason'])

        return reading

    # ──────────────────────────────────────────
    # Validações
    # ──────────────────────────────────────────
    @staticmethod
    def _validate_meter_active(meter: WaterMeter):
        if meter.status == 'INACTIVE':
            raise ReadingValidationError(
                f"Medidor {meter.serial_number} está inativo. "
                "Ative-o antes de registrar leituras."
            )

    @staticmethod
    def _validate_reading_value(meter: WaterMeter, value: Decimal):
        if value < 0:
            raise ReadingValidationError(
                "O valor de leitura não pode ser negativo."
            )

        last = (
            MeterReading.objects
            .filter(meter=meter)
            .order_by('-reading_date')
            .first()
        )
        if last and value < last.reading_value:
            raise ReadingValidationError(
                f"Valor informado ({value} m³) é menor que a última leitura "
                f"({last.reading_value} m³) em {last.reading_date.date()}. "
                "Verifique se o hidrômetro foi substituído."
            )

    @staticmethod
    def _validate_reading_date(meter: WaterMeter, reading_date):
        last = (
            MeterReading.objects
            .filter(meter=meter)
            .order_by('-reading_date')
            .first()
        )
        if last and reading_date <= last.reading_date:
            raise ReadingValidationError(
                f"A data da leitura ({reading_date}) deve ser posterior "
                f"à última leitura ({last.reading_date})."
            )
        if reading_date > timezone.now():
            raise ReadingValidationError(
                "Não é possível registrar leituras com data futura."
            )

    # ──────────────────────────────────────────
    # Cálculo de consumo
    # ──────────────────────────────────────────
    @staticmethod
    def calculate_consumption(reading: MeterReading) -> dict:
        """
        Calcula o consumo entre esta leitura e a anterior.
        Retorna dict com consumption_m3, previous_reading, days_elapsed.
        """
        previous = (
            MeterReading.objects
            .filter(
                meter=reading.meter,
                reading_date__lt=reading.reading_date,
            )
            .order_by('-reading_date')
            .first()
        )

        if previous is None:
            return {
                'consumption_m3': None,
                'previous_reading': None,
                'days_elapsed': None,
                'daily_avg_m3': None,
            }

        consumption = reading.reading_value - previous.reading_value
        delta = reading.reading_date - previous.reading_date
        days = max(delta.days, 1)

        return {
            'consumption_m3': float(consumption),
            'previous_reading': {
                'value': float(previous.reading_value),
                'date': previous.reading_date,
            },
            'days_elapsed': days,
            'daily_avg_m3': round(float(consumption) / days, 4),
        }

    # ──────────────────────────────────────────
    # Detecção de anomalias
    # ──────────────────────────────────────────
    @classmethod
    def detect_anomaly(cls, reading: MeterReading) -> dict:
        """
        Verifica se a leitura é anômala comparando com histórico.
        Retorna {'is_anomaly': bool, 'reason': str | None}.
        """
        consumption_data = cls.calculate_consumption(reading)

        if consumption_data['consumption_m3'] is None:
            # Primeira leitura: sem histórico para comparar
            return {'is_anomaly': False, 'reason': None}

        consumption = Decimal(str(consumption_data['consumption_m3']))

        # Anomalia 1: consumo zero inesperado
        if ANOMALY_ZERO_ALERT and consumption == 0:
            past_non_zero = (
                MeterReading.objects
                .filter(meter=reading.meter, reading_date__lt=reading.reading_date)
                .count()
            )
            if past_non_zero >= 2:
                return {
                    'is_anomaly': True,
                    'reason': 'Consumo zero inesperado. Possível vazamento interno ou erro de leitura.',
                }

        # Anomalia 2: consumo muito acima da média histórica
        historical = cls._get_historical_consumptions(reading)
        if len(historical) >= ANOMALY_MIN_READINGS:
            avg = sum(historical) / len(historical)
            if avg > 0 and consumption > avg * Decimal(str(ANOMALY_MULTIPLIER)):
                return {
                    'is_anomaly': True,
                    'reason': (
                        f"Consumo ({consumption} m³) é "
                        f"{round(float(consumption / avg), 1)}× acima da média "
                        f"histórica ({round(float(avg), 2)} m³). "
                        "Possível vazamento ou erro de leitura."
                    ),
                }

        return {'is_anomaly': False, 'reason': None}

    @staticmethod
    def _get_historical_consumptions(reading: MeterReading) -> list:
        """
        Retorna lista de consumos (m³) das últimas N leituras anteriores.
        """
        past_readings = list(
            MeterReading.objects
            .filter(meter=reading.meter, reading_date__lt=reading.reading_date)
            .order_by('-reading_date')[:12]   # últimos 12 períodos
        )

        consumptions = []
        for i in range(len(past_readings) - 1):
            diff = past_readings[i].reading_value - past_readings[i + 1].reading_value
            if diff >= 0:
                consumptions.append(diff)

        return consumptions

    # ──────────────────────────────────────────
    # Relatório por medidor
    # ──────────────────────────────────────────
    @staticmethod
    def get_meter_consumption_history(meter: WaterMeter, limit: int = 12) -> list:
        """
        Retorna histórico de consumo por período para um medidor.
        Útil para gráficos no dashboard.
        """
        readings = list(
            MeterReading.objects
            .filter(meter=meter)
            .order_by('reading_date')
        )

        history = []
        for i in range(1, len(readings)):
            curr = readings[i]
            prev = readings[i - 1]
            delta = curr.reading_date - prev.reading_date
            days = max(delta.days, 1)
            consumption = float(curr.reading_value - prev.reading_value)

            history.append({
                'period_start': prev.reading_date.date(),
                'period_end': curr.reading_date.date(),
                'reading_id': str(curr.id),
                'consumption_m3': consumption,
                'days_elapsed': days,
                'daily_avg_m3': round(consumption / days, 4),
                'is_anomaly': getattr(curr, 'anomaly_flag', False),
            })

        return history[-limit:]
