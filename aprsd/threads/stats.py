import logging
import threading
import time

from loguru import logger
from oslo_config import cfg

from aprsd.threads import APRSDThread
from aprsd.utils import objectstore

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')
LOGU = logger


class StatsStore(objectstore.ObjectStoreMixin):
    """Container to save the stats from the collector."""

    def __init__(self):
        self.lock = threading.RLock()

    def add(self, stats: dict):
        with self.lock:
            self.data = stats


class APRSDStatsStoreThread(APRSDThread):
    """Save APRSD Stats to disk periodically."""

    # how often in seconds to write the file
    save_interval = 10

    def __init__(self):
        super().__init__('StatsStore')

    def loop(self):
        if self.loop_count % self.save_interval == 0:
            # Lazy import to avoid circular dependency
            from aprsd.stats import collector

            stats = collector.Collector().collect()
            ss = StatsStore()
            ss.add(stats)
            ss.save()

        time.sleep(1)
        return True


class StatsLogThread(APRSDThread):
    """Log the stats from the PacketList."""

    def __init__(self):
        super().__init__('PacketStatsLog')
        self._last_total_rx = 0
        self.period = 10
        self.start_time = time.time()

    def loop(self):
        if self.loop_count % self.period == 0:
            # Lazy imports to avoid circular dependency
            from aprsd.packets import seen_list
            from aprsd.stats import collector

            # log the stats every 10 seconds
            stats_json = collector.Collector().collect(serializable=True)
            stats = stats_json['PacketList']
            total_rx = stats['rx']
            rx_delta = total_rx - self._last_total_rx
            rate = rx_delta / self.period

            # Get unique callsigns count from SeenList stats
            seen_list_instance = seen_list.SeenList()
            # stats() returns data while holding lock internally, so copy it immediately
            seen_list_stats = seen_list_instance.stats()
            seen_list_instance.save()
            # Copy the stats to avoid holding references to locked data
            seen_list_stats = seen_list_stats.copy()
            unique_callsigns_count = len(seen_list_stats)

            # Calculate uptime
            elapsed = time.time() - self.start_time
            elapsed_minutes = elapsed / 60
            elapsed_hours = elapsed / 3600

            # Log summary stats
            LOGU.opt(colors=True).info(
                f'<green>RX Rate: {rate:.2f} pps</green>  '
                f'<yellow>Total RX: {total_rx}</yellow> '
                f'<red>RX Last {self.period} secs: {rx_delta}</red> '
            )
            LOGU.opt(colors=True).info(
                f'<cyan>Uptime: {elapsed:.0f}s ({elapsed_minutes:.1f}m / {elapsed_hours:.2f}h)</cyan>  '
                f'<magenta>Unique Callsigns: {unique_callsigns_count}</magenta>',
            )
            self._last_total_rx = total_rx

            # Log individual type stats, sorted by RX count (descending)
            sorted_types = sorted(
                stats['types'].items(), key=lambda x: x[1]['rx'], reverse=True
            )
            for k, v in sorted_types:
                # Calculate percentage of this packet type compared to total RX
                percentage = (v['rx'] / total_rx * 100) if total_rx > 0 else 0.0
                # Format values first, then apply colors
                packet_type_str = f'{k:<15}'
                rx_count_str = f'{v["rx"]:6d}'
                tx_count_str = f'{v["tx"]:6d}'
                percentage_str = f'{percentage:5.1f}%'
                # Use different colors for RX count based on threshold (matching mqtt_injest.py)
                rx_color_tag = (
                    'green' if v['rx'] > 100 else 'yellow' if v['rx'] > 10 else 'red'
                )
                LOGU.opt(colors=True).info(
                    f'  <cyan>{packet_type_str}</cyan>: '
                    f'<{rx_color_tag}>RX: {rx_count_str}</{rx_color_tag}> '
                    f'<red>TX: {tx_count_str}</red> '
                    f'<magenta>({percentage_str})</magenta>',
                )

            # Extract callsign counts from seen_list stats
            callsign_counts = {}
            for callsign, data in seen_list_stats.items():
                if isinstance(data, dict) and 'count' in data:
                    callsign_counts[callsign] = data['count']

            # Sort callsigns by packet count (descending) and get top 10
            sorted_callsigns = sorted(
                callsign_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]

            # Log top 10 callsigns
            if sorted_callsigns:
                LOGU.opt(colors=True).info(
                    '<cyan>Top 10 Callsigns by Packet Count:</cyan>'
                )
                total_ranks = len(sorted_callsigns)
                for rank, (callsign, count) in enumerate(sorted_callsigns, 1):
                    # Use different colors based on rank: most packets (rank 1) = red,
                    # least packets (last rank) = green, middle = yellow
                    if rank == 1:
                        count_color_tag = 'red'
                    elif rank == total_ranks:
                        count_color_tag = 'green'
                    else:
                        count_color_tag = 'yellow'
                    LOGU.opt(colors=True).info(
                        f'  <cyan>{rank:2d}.</cyan> '
                        f'<white>{callsign:<12}</white>: '
                        f'<{count_color_tag}>{count:6d} packets</{count_color_tag}>',
                    )

        time.sleep(1)
        return True
