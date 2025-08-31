#!/usr/bin/env python3
"""
KLSE Integration Scripts
Seamlessly switch between US and Malaysian trading systems
"""

import os
import sys
import json
import shutil
import pandas as pd
from datetime import datetime
import argparse
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradingSystemManager:
    """
    Manage multiple trading systems (US and KLSE)
    """
    
    def __init__(self, workspace_root: str = None):
        self.workspace_root = workspace_root or os.getcwd()
        self.config_file = os.path.join(self.workspace_root, "system_config.json")
        
        # System definitions
        self.systems = {
            "US": {
                "name": "US Micro-Cap Trading System",
                "description": "Original ChatGPT micro-cap experiment (US stocks)",
                "currency": "USD",
                "starting_capital": 100.0,
                "files": {
                    "trading_script": "Trading_Script.py",
                    "enhanced_script": "Trading_Script_Enhanced.py", 
                    "portfolio_csv": "chatgpt_portfolio_update.csv",
                    "trades_csv": "chatgpt_trade_log.csv",
                    "graph_script": "Generate_Graph.py",
                    "enhanced_graph": "Generate_Graph_Enhanced.py"
                },
                "directories": ["Scripts and CSV Files/"]
            },
            "KLSE": {
                "name": "Malaysian KLSE Trading System",
                "description": "Malaysian micro-cap experiment (KLSE stocks)",
                "currency": "MYR", 
                "starting_capital": 10000.0,
                "files": {
                    "portfolio_manager": "KLSE_System/klse_portfolio_manager.py",
                    "trading_engine": "KLSE_System/klse_trading_engine.py",
                    "visualization": "KLSE_System/klse_visualization.py",
                    "microcap_db": "KLSE_System/klse_microcap_database.py",
                    "portfolio_csv": "KLSE_System/klse_portfolio.csv",
                    "trades_csv": "KLSE_System/klse_trades.csv",
                    "daily_updates": "KLSE_System/klse_daily_updates.csv"
                },
                "directories": ["KLSE_System/", "KLSE_System/charts/"]
            }
        }
        
        # Load or create configuration
        self.config = self._load_config()
        
        logger.info("Trading System Manager initialized")
    
    def _load_config(self) -> Dict:
        """Load or create system configuration"""
        default_config = {
            "current_system": "US",
            "last_switched": datetime.now().isoformat(),
            "system_states": {
                "US": {"active": True, "last_run": None, "status": "ready"},
                "KLSE": {"active": False, "last_run": None, "status": "ready"}
            },
            "backup_enabled": True,
            "auto_backup_days": 7
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge any new default settings
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                logger.warning(f"Error loading config: {e}, using defaults")
                
        return default_config
    
    def _save_config(self):
        """Save system configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        status = {
            "current_system": self.config["current_system"],
            "last_switched": self.config["last_switched"],
            "systems": {}
        }
        
        for system_name, system_info in self.systems.items():
            # Check if system files exist
            files_exist = []
            for file_key, file_path in system_info["files"].items():
                full_path = os.path.join(self.workspace_root, file_path)
                files_exist.append(os.path.exists(full_path))
            
            # Check directories
            dirs_exist = []
            for dir_path in system_info["directories"]:
                full_path = os.path.join(self.workspace_root, dir_path)
                dirs_exist.append(os.path.exists(full_path))
            
            system_status = {
                "name": system_info["name"],
                "description": system_info["description"],
                "currency": system_info["currency"],
                "files_ready": all(files_exist),
                "directories_ready": all(dirs_exist),
                "files_count": len([f for f in files_exist if f]),
                "total_files": len(files_exist),
                "active": self.config["system_states"][system_name]["active"],
                "last_run": self.config["system_states"][system_name]["last_run"],
                "status": self.config["system_states"][system_name]["status"]
            }
            
            status["systems"][system_name] = system_status
        
        return status
    
    def switch_system(self, target_system: str, backup_current: bool = True) -> bool:
        """Switch to different trading system"""
        if target_system not in self.systems:
            logger.error(f"Unknown system: {target_system}")
            return False
        
        current_system = self.config["current_system"]
        
        if current_system == target_system:
            logger.info(f"Already using {target_system} system")
            return True
        
        logger.info(f"Switching from {current_system} to {target_system}")
        
        # Backup current system if requested
        if backup_current:
            backup_success = self.backup_system(current_system)
            if not backup_success:
                logger.warning("Backup failed, but continuing with switch")
        
        # Deactivate current system
        self.config["system_states"][current_system]["active"] = False
        
        # Activate target system
        self.config["system_states"][target_system]["active"] = True
        self.config["current_system"] = target_system
        self.config["last_switched"] = datetime.now().isoformat()
        
        # Save configuration
        self._save_config()
        
        logger.info(f"✅ Switched to {target_system} system")
        return True
    
    def backup_system(self, system_name: str) -> bool:
        """Create backup of system data"""
        if system_name not in self.systems:
            logger.error(f"Unknown system: {system_name}")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.workspace_root, f"backups/{system_name}_{timestamp}")
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            
            system_info = self.systems[system_name]
            
            # Backup files
            files_backed_up = 0
            for file_key, file_path in system_info["files"].items():
                source_path = os.path.join(self.workspace_root, file_path)
                if os.path.exists(source_path):
                    dest_path = os.path.join(backup_dir, os.path.basename(file_path))
                    shutil.copy2(source_path, dest_path)
                    files_backed_up += 1
            
            # Backup directories
            dirs_backed_up = 0
            for dir_path in system_info["directories"]:
                source_dir = os.path.join(self.workspace_root, dir_path)
                if os.path.exists(source_dir):
                    dest_dir = os.path.join(backup_dir, os.path.basename(dir_path.rstrip('/')))
                    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
                    dirs_backed_up += 1
            
            # Create backup manifest
            manifest = {
                "system": system_name,
                "backup_time": datetime.now().isoformat(),
                "files_backed_up": files_backed_up,
                "directories_backed_up": dirs_backed_up,
                "backup_path": backup_dir
            }
            
            with open(os.path.join(backup_dir, "backup_manifest.json"), 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"✅ Backed up {system_name}: {files_backed_up} files, {dirs_backed_up} directories")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed for {system_name}: {e}")
            return False
    
    def run_system_command(self, system_name: str, command: str, **kwargs) -> Dict:
        """Run command on specified system"""
        if system_name not in self.systems:
            return {"success": False, "error": f"Unknown system: {system_name}"}
        
        if system_name != self.config["current_system"]:
            logger.warning(f"Running command on inactive system: {system_name}")
        
        system_info = self.systems[system_name]
        
        try:
            if system_name == "US":
                return self._run_us_command(command, **kwargs)
            elif system_name == "KLSE":
                return self._run_klse_command(command, **kwargs)
            else:
                return {"success": False, "error": f"No command handler for {system_name}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_us_command(self, command: str, **kwargs) -> Dict:
        """Run US system command"""
        if command == "daily_update":
            # Run US daily trading update
            script_path = os.path.join(self.workspace_root, "Trading_Script_Enhanced.py")
            if os.path.exists(script_path):
                # Execute the trading script
                os.system(f"cd {self.workspace_root} && python Trading_Script_Enhanced.py")
                return {"success": True, "message": "US daily update completed"}
            else:
                return {"success": False, "error": "US trading script not found"}
        
        elif command == "generate_graph":
            # Generate US performance graph
            script_path = os.path.join(self.workspace_root, "Generate_Graph_Enhanced.py")
            if os.path.exists(script_path):
                os.system(f"cd {self.workspace_root} && python Generate_Graph_Enhanced.py")
                return {"success": True, "message": "US graph generated"}
            else:
                return {"success": False, "error": "US graph script not found"}
        
        else:
            return {"success": False, "error": f"Unknown US command: {command}"}
    
    def _run_klse_command(self, command: str, **kwargs) -> Dict:
        """Run KLSE system command"""
        if command == "daily_update":
            # Run KLSE daily trading update
            script_path = os.path.join(self.workspace_root, "KLSE_System/klse_trading_engine.py")
            if os.path.exists(script_path):
                os.system(f"cd {self.workspace_root} && python KLSE_System/klse_trading_engine.py --action daily")
                return {"success": True, "message": "KLSE daily update completed"}
            else:
                return {"success": False, "error": "KLSE trading engine not found"}
        
        elif command == "generate_charts":
            # Generate KLSE visualization charts
            script_path = os.path.join(self.workspace_root, "KLSE_System/klse_visualization.py")
            if os.path.exists(script_path):
                os.system(f"cd {self.workspace_root} && python KLSE_System/klse_visualization.py --action all")
                return {"success": True, "message": "KLSE charts generated"}
            else:
                return {"success": False, "error": "KLSE visualization script not found"}
        
        elif command == "update_database":
            # Update KLSE micro-cap database
            script_path = os.path.join(self.workspace_root, "KLSE_System/klse_microcap_database.py")
            if os.path.exists(script_path):
                os.system(f"cd {self.workspace_root} && python KLSE_System/klse_microcap_database.py --action update")
                return {"success": True, "message": "KLSE database updated"}
            else:
                return {"success": False, "error": "KLSE database script not found"}
        
        else:
            return {"success": False, "error": f"Unknown KLSE command: {command}"}
    
    def get_performance_comparison(self) -> Dict:
        """Compare performance between US and KLSE systems"""
        comparison = {
            "comparison_date": datetime.now().isoformat(),
            "systems": {}
        }
        
        # US System Performance
        us_portfolio_file = os.path.join(self.workspace_root, "Scripts and CSV Files/chatgpt_portfolio_update.csv")
        if os.path.exists(us_portfolio_file):
            try:
                us_data = pd.read_csv(us_portfolio_file)
                if not us_data.empty:
                    latest_us = us_data.iloc[-1]
                    comparison["systems"]["US"] = {
                        "currency": "USD",
                        "current_value": latest_us.get("Total Equity", 0),
                        "starting_value": 100.0,
                        "return_pct": ((latest_us.get("Total Equity", 100) - 100) / 100) * 100,
                        "last_update": latest_us.get("Date", "Unknown"),
                        "data_available": True
                    }
            except Exception as e:
                comparison["systems"]["US"] = {"data_available": False, "error": str(e)}
        else:
            comparison["systems"]["US"] = {"data_available": False, "error": "Portfolio file not found"}
        
        # KLSE System Performance
        klse_portfolio_file = os.path.join(self.workspace_root, "KLSE_System/klse_daily_updates.csv")
        if os.path.exists(klse_portfolio_file):
            try:
                klse_data = pd.read_csv(klse_portfolio_file)
                if not klse_data.empty:
                    latest_klse = klse_data.iloc[-1]
                    comparison["systems"]["KLSE"] = {
                        "currency": "MYR",
                        "current_value": latest_klse.get("total_equity_myr", 0),
                        "starting_value": 10000.0,
                        "return_pct": latest_klse.get("total_return_pct", 0),
                        "last_update": latest_klse.get("date", "Unknown"),
                        "data_available": True
                    }
            except Exception as e:
                comparison["systems"]["KLSE"] = {"data_available": False, "error": str(e)}
        else:
            comparison["systems"]["KLSE"] = {"data_available": False, "error": "Portfolio file not found"}
        
        return comparison
    
    def run_dual_system_update(self) -> Dict:
        """Run daily updates on both systems"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "us_result": {"success": False},
            "klse_result": {"success": False}
        }
        
        logger.info("Running dual system update...")
        
        # Run US system update
        try:
            results["us_result"] = self._run_us_command("daily_update")
            logger.info("✅ US system updated")
        except Exception as e:
            results["us_result"] = {"success": False, "error": str(e)}
            logger.error(f"❌ US system update failed: {e}")
        
        # Run KLSE system update
        try:
            results["klse_result"] = self._run_klse_command("daily_update")
            logger.info("✅ KLSE system updated")
        except Exception as e:
            results["klse_result"] = {"success": False, "error": str(e)}
            logger.error(f"❌ KLSE system update failed: {e}")
        
        # Update system states
        if results["us_result"]["success"]:
            self.config["system_states"]["US"]["last_run"] = datetime.now().isoformat()
            self.config["system_states"]["US"]["status"] = "updated"
        
        if results["klse_result"]["success"]:
            self.config["system_states"]["KLSE"]["last_run"] = datetime.now().isoformat()
            self.config["system_states"]["KLSE"]["status"] = "updated"
        
        self._save_config()
        
        return results

def main():
    """Main integration script"""
    parser = argparse.ArgumentParser(description='Trading System Integration Manager')
    parser.add_argument('--action', choices=['status', 'switch', 'backup', 'run', 'compare', 'dual-update'], 
                       default='status', help='Action to perform')
    parser.add_argument('--system', choices=['US', 'KLSE'], help='Target system')
    parser.add_argument('--command', help='Command to run on system')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup when switching')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = TradingSystemManager()
    
    if args.action == 'status':
        # Show system status
        status = manager.get_system_status()
        print("🔄 TRADING SYSTEMS STATUS")
        print("=" * 60)
        print(f"Current System: {status['current_system']}")
        print(f"Last Switched: {status['last_switched']}")
        print()
        
        for system_name, system_info in status['systems'].items():
            active_marker = "🟢" if system_info['active'] else "🔴"
            ready_marker = "✅" if system_info['files_ready'] else "❌"
            
            print(f"{active_marker} {system_name} - {system_info['name']}")
            print(f"   {ready_marker} Files: {system_info['files_count']}/{system_info['total_files']}")
            print(f"   💰 Currency: {system_info['currency']}")
            print(f"   📊 Status: {system_info['status']}")
            print(f"   ⏰ Last Run: {system_info['last_run'] or 'Never'}")
            print()
    
    elif args.action == 'switch':
        if not args.system:
            print("❌ Please specify --system (US or KLSE)")
            return
        
        backup = not args.no_backup
        success = manager.switch_system(args.system, backup_current=backup)
        
        if success:
            print(f"✅ Switched to {args.system} system")
        else:
            print(f"❌ Failed to switch to {args.system} system")
    
    elif args.action == 'backup':
        if not args.system:
            print("❌ Please specify --system (US or KLSE)")
            return
        
        success = manager.backup_system(args.system)
        
        if success:
            print(f"✅ Backed up {args.system} system")
        else:
            print(f"❌ Failed to backup {args.system} system")
    
    elif args.action == 'run':
        if not args.system or not args.command:
            print("❌ Please specify --system and --command")
            return
        
        result = manager.run_system_command(args.system, args.command)
        
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
    
    elif args.action == 'compare':
        # Compare system performance
        comparison = manager.get_performance_comparison()
        
        print("📊 SYSTEM PERFORMANCE COMPARISON")
        print("=" * 50)
        
        for system_name, system_data in comparison['systems'].items():
            if system_data.get('data_available'):
                return_pct = system_data['return_pct']
                return_symbol = "🟢" if return_pct >= 0 else "🔴"
                
                print(f"{return_symbol} {system_name} System:")
                print(f"   Current Value: {system_data['current_value']:.2f} {system_data['currency']}")
                print(f"   Starting Value: {system_data['starting_value']:.2f} {system_data['currency']}")
                print(f"   Return: {return_pct:+.2f}%")
                print(f"   Last Update: {system_data['last_update']}")
                print()
            else:
                print(f"❌ {system_name} System: {system_data.get('error', 'No data')}")
                print()
    
    elif args.action == 'dual-update':
        # Run updates on both systems
        print("🔄 Running dual system update...")
        results = manager.run_dual_system_update()
        
        print("\n📊 DUAL UPDATE RESULTS:")
        print("-" * 30)
        
        us_status = "✅" if results["us_result"]["success"] else "❌"
        klse_status = "✅" if results["klse_result"]["success"] else "❌"
        
        print(f"{us_status} US System: {results['us_result'].get('message', results['us_result'].get('error', 'Unknown'))}")
        print(f"{klse_status} KLSE System: {results['klse_result'].get('message', results['klse_result'].get('error', 'Unknown'))}")

if __name__ == "__main__":
    main()
