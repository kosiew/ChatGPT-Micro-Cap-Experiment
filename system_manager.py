#!/usr/bin/env python3
"""
Trading System Manager
Easy switching between original and enhanced trading systems
"""

import os
import shutil
import sys
from datetime import datetime

class TradingSystemManager:
    def __init__(self):
        self.scripts_dir = "Scripts and CSV Files"
        self.original_script = "Trading_Script_Original_Backup.py"
        self.enhanced_script = "Trading_Script_Enhanced.py"
        self.active_script = "Trading_Script.py"
        
    def status(self):
        """Show current system status"""
        print("🔍 Trading System Status")
        print("=" * 40)
        
        # Check which system is currently active
        if os.path.exists(os.path.join(self.scripts_dir, self.active_script)):
            with open(os.path.join(self.scripts_dir, self.active_script), 'r') as f:
                content = f.read()
                if "Enhanced Trading Script" in content:
                    current_system = "Enhanced"
                    emoji = "🚀"
                else:
                    current_system = "Original"
                    emoji = "📊"
        else:
            current_system = "Unknown"
            emoji = "❓"
        
        print(f"{emoji} Active System: {current_system}")
        
        # Check file availability
        files_status = {
            "Original Backup": self.original_script,
            "Enhanced Script": self.enhanced_script,
            "Active Script": self.active_script
        }
        
        print(f"\n📁 File Status:")
        for name, filename in files_status.items():
            path = os.path.join(self.scripts_dir, filename)
            exists = "✅" if os.path.exists(path) else "❌"
            print(f"   {exists} {name}: {filename}")
        
        # Check redundant data fetcher
        redundant_fetcher = "redundant_data_fetcher.py"
        fetcher_exists = "✅" if os.path.exists(redundant_fetcher) else "❌"
        print(f"   {fetcher_exists} Redundant Fetcher: {redundant_fetcher}")
        
        return current_system
    
    def switch_to_enhanced(self):
        """Switch to enhanced trading system"""
        print("🚀 Switching to Enhanced Trading System")
        print("=" * 40)
        
        if not os.path.exists(os.path.join(self.scripts_dir, self.enhanced_script)):
            print(f"❌ Enhanced script not found: {self.enhanced_script}")
            return False
        
        # Backup current active script if it's not already the enhanced one
        active_path = os.path.join(self.scripts_dir, self.active_script)
        if os.path.exists(active_path):
            backup_name = f"Trading_Script_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = os.path.join(self.scripts_dir, backup_name)
            shutil.copy2(active_path, backup_path)
            print(f"💾 Current script backed up as: {backup_name}")
        
        # Copy enhanced script to active position
        enhanced_path = os.path.join(self.scripts_dir, self.enhanced_script)
        shutil.copy2(enhanced_path, active_path)
        
        print("✅ Enhanced system activated!")
        print("🔄 Features enabled:")
        print("   - Redundant data sources")
        print("   - Automatic failover")
        print("   - Enhanced logging")
        print("   - Performance monitoring")
        
        return True
    
    def switch_to_original(self):
        """Switch to original trading system"""
        print("📊 Switching to Original Trading System")
        print("=" * 40)
        
        if not os.path.exists(os.path.join(self.scripts_dir, self.original_script)):
            print(f"❌ Original script backup not found: {self.original_script}")
            return False
        
        # Backup current active script
        active_path = os.path.join(self.scripts_dir, self.active_script)
        if os.path.exists(active_path):
            backup_name = f"Trading_Script_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = os.path.join(self.scripts_dir, backup_name)
            shutil.copy2(active_path, backup_path)
            print(f"💾 Current script backed up as: {backup_name}")
        
        # Copy original script to active position
        original_path = os.path.join(self.scripts_dir, self.original_script)
        shutil.copy2(original_path, active_path)
        
        print("✅ Original system restored!")
        print("📊 Using standard yfinance data source")
        
        return True
    
    def test_current_system(self):
        """Test the currently active trading system"""
        print("🧪 Testing Current Trading System")
        print("=" * 40)
        
        # Change to scripts directory and run test
        original_dir = os.getcwd()
        try:
            os.chdir(self.scripts_dir)
            
            # Check if current system supports test mode
            if os.path.exists(self.active_script):
                import subprocess
                result = subprocess.run([sys.executable, self.active_script, "test"], 
                                      capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print("✅ System test successful!")
                    print("📊 Test output:")
                    print(result.stdout[-500:])  # Show last 500 chars
                else:
                    print("❌ System test failed!")
                    print("Error output:")
                    print(result.stderr[-500:])
                    
            else:
                print(f"❌ Active script not found: {self.active_script}")
                
        except subprocess.TimeoutExpired:
            print("⏰ Test timed out after 60 seconds")
        except Exception as e:
            print(f"❌ Test error: {e}")
        finally:
            os.chdir(original_dir)
    
    def system_health(self):
        """Check system health (enhanced mode only)"""
        print("🏥 System Health Check")
        print("=" * 40)
        
        current_system = self.status()
        
        if current_system != "Enhanced":
            print("⚠️  Health monitoring only available in Enhanced mode")
            print("💡 Switch to enhanced system to enable monitoring")
            return
        
        try:
            # Import health check from enhanced system
            sys.path.append(self.scripts_dir)
            from Trading_Script_Enhanced import data_fetcher
            
            if data_fetcher:
                performance = data_fetcher.get_source_performance()
                
                if performance:
                    print("📈 Data Source Performance:")
                    for source, stats in performance.items():
                        status_emoji = "✅" if stats['success_rate'] >= 90 else \
                                     "⚠️" if stats['success_rate'] >= 70 else "❌"
                        print(f"   {status_emoji} {source}: {stats['success_rate']}% success ({stats['successes']}/{stats['attempts']})")
                else:
                    print("📊 No performance data available yet")
                    print("💡 Process some trades first to generate statistics")
            else:
                print("⚠️  Enhanced data fetcher not initialized")
                
        except Exception as e:
            print(f"❌ Health check failed: {e}")

def main():
    manager = TradingSystemManager()
    
    if len(sys.argv) < 2:
        print("🔧 Trading System Manager")
        print("=" * 30)
        print("Usage:")
        print("  python system_manager.py status      # Show current system")
        print("  python system_manager.py enhanced    # Switch to enhanced")
        print("  python system_manager.py original    # Switch to original")
        print("  python system_manager.py test        # Test current system")
        print("  python system_manager.py health      # Check system health")
        print()
        manager.status()
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        manager.status()
    elif command == "enhanced":
        manager.switch_to_enhanced()
    elif command == "original":
        manager.switch_to_original()
    elif command == "test":
        manager.test_current_system()
    elif command == "health":
        manager.system_health()
    else:
        print(f"❌ Unknown command: {command}")
        print("💡 Use: status, enhanced, original, test, or health")

if __name__ == "__main__":
    main()
