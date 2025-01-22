from typing import List, Dict, Any
from collections import defaultdict
from .transaction import Transaction

class Subtensor:
    """
    Subtensor blockchain simulation environment.

    across multiple subnets and accounts.

    Attributes:
        subnets: Dict[int, Subnet] mapping subnet IDs to Subnet objects
        accounts: Dict[int, Account] mapping account IDs to Account objects
        transaction_blocks: Dict[int, List[Transaction]] mapping blocks to transactions
        tao_supply: Total TAO token supply
        global_split: Ratio (0-1) between global/local rewards
        balanced: If True, uses balanced emission mode
        initial_root_weight: Starting root subnet weight
        root_weight: Current root subnet weight
        blocks: Total simulation blocks
        log_interval: State logging frequency
    """
    def __init__(self, subnets, accounts, transactions, tao_supply,
                 global_split, balanced, root_weight, blocks, n_steps,
                 injection_range=(0.0, 1.0)):
        self.subnets = {s.id: s for s in subnets}
        self.accounts = {a.id: a for a in accounts}
        self.transaction_blocks = self._organize_transactions(transactions)
        self.tao_supply = tao_supply
        self.global_split = global_split
        self.balanced = balanced
        self.initial_root_weight = root_weight
        self.root_weight = root_weight
        self.blocks = blocks
        self.log_interval = int(blocks/n_steps)
        self.injection_range = injection_range

    def _organize_transactions(self, transactions: List[Transaction]) -> Dict[int, List[Transaction]]:
        """
        Organize transactions by block number for efficient processing.

        Args:
            transactions (List[Transaction]): List of transactions to organize

        Returns:
            Dict[int, List[Transaction]]: Mapping of block numbers to lists of transactions
        """
        transaction_dict = defaultdict(list)
        for transaction in transactions:
            transaction_dict[transaction.block].append(transaction)
        return dict(transaction_dict)

    def _parse_amount(self, amount: str, total: float) -> float:
        """
        Parse amount string into a float value.

        Supports formats:
            - 'all': Returns total amount
            - '50%': Returns 50% of total
            - '123': Returns float value 123.0

        Args:
            amount (str): Amount string to parse
            total (float): Total available amount for percentage calculations

        Returns:
            float: Parsed amount value
        """
        if amount == 'all':
            return total
        if '%' in amount:
            return total * float(amount.strip('%')) / 100
        return float(amount)

    def _update_root_weight(self, current_block: int):
        """
        Update root subnet weight based on current block.

        Formula:
            weight_decrease = initial_root_weight / blocks
            new_weight = max(0, initial_weight - (block * decrease))

        Args:
            current_block (int): Current block number
        """
        weight_decrease_per_block = self.initial_root_weight / self.blocks
        self.root_weight = max(0.0, self.initial_root_weight - (current_block * weight_decrease_per_block))

    def _process_block_step(self):
        """
        Process a single block step in the simulation.

        For each block:
        1. Calculate emission distribution across subnets based on tao holdings
        2. Update global tao supply:
           - If sum(alpha_prices) < min_range or not balanced: tao_supply += emission_val
           - Otherwise: no change
        3. For each non-root subnet:
           - If sum(alpha_prices) < min_range or not balanced:
             Inject tao_amount = subnet_emission_share * emission_val
           - If sum(alpha_prices) >= max_range and balanced:
             Inject alpha_amount = emission_val
           - If min_range <= sum(alpha_prices) <= max_range and balanced:
             Inject both tao_amount and alpha_amount = emission_val
           - Calculate dividends per account based on stakes
           - Distribute alpha dividends: 
             account_alpha_stake += dividend_share * emission_val

        The emission_val is fixed at 1.0 tao per block.
        """
        '''
        emit = self._calculate_emission()
        sum_prices = sum(s.alpha_price() for s in self.subnets.values() if not s.is_root)
        emission_val = 1
        min_range, max_range = self.injection_range

        if sum_prices < min_range or not self.balanced:
            self.tao_supply += emission_val

        for subnet in self.subnets.values():
            if subnet.is_root:
                continue

            tao_amount = emit.get(subnet.id, 0.0) * emission_val \
                if sum_prices < min_range or not self.balanced else 0.0
            alpha_amount = emission_val if sum_prices > max_range and self.balanced else 0.0
            
            if min_range <= sum_prices <= max_range and self.balanced:
                tao_amount = emit.get(subnet.id, 0.0) * emission_val
                alpha_amount = emission_val

            subnet.inject(tao_amount, alpha_amount, emission_val)

            dividends = self._calculate_dividends(subnet.id)
            for acc_id, div in dividends.items():
                self.accounts[acc_id].alpha_stakes[subnet.id] = \
                    self.accounts[acc_id].alpha_stakes.get(subnet.id, 0.0) + \
                    div * emission_val

        '''
        emit = self._calculate_emission()
        sum_prices = sum(s.alpha_price() for s in self.subnets.values() if not s.is_root)
        emission_val = 1

        if sum_prices < 1.0 or not self.balanced:
            self.tao_supply += emission_val

        for subnet in self.subnets.values():
            if subnet.is_root:
                continue

            tao_amount = emit.get(subnet.id, 0.0) * emission_val \
                if sum_prices < 1.0 or not self.balanced else 0.0
            alpha_amount = emission_val if sum_prices >= 1.0 and self.balanced else 0.0

            dividends = self._calculate_dividends(subnet.id)
            for acc_id, div in dividends.items():
                if subnet.id in self.accounts[acc_id].registered_subnets:
                    self.accounts[acc_id].alpha_stakes[subnet.id] = \
                        self.accounts[acc_id].alpha_stakes.get(subnet.id, 0.0) + \
                        div * emission_val

            subnet.inject(tao_amount, alpha_amount, emission_val)

    def _execute_transaction(self, transaction: Transaction):
        """
        Execute a single transaction in the simulation.

        For buy (stake) actions:
            1. Parse amount from transaction.amount string
            2. Convert tao_amount to alpha via subnet.stake()
            3. Add alpha_bought to account's subnet stakes
            4. Subtract tao_amount from account's free balance

        For sell (unstake) actions:
            1. Parse amount from transaction.amount string
            2. Convert alpha_amount to tao via subnet.unstake()
            3. Subtract alpha_amount from account's subnet stakes
            4. Add tao_bought to account's free balance

        Args:
            transaction (Transaction): Transaction object containing transaction details
        """
        account = self.accounts.get(transaction.account_id)
        subnet = self.subnets.get(transaction.subnet_id)
        if not account or not subnet:
            return

        if transaction.action == 'stake':
            tao_amount = self._parse_amount(transaction.amount, account.free_balance)
            alpha_bought = subnet.stake(tao_amount)
            account.alpha_stakes[transaction.subnet_id] = account.alpha_stakes.get(transaction.subnet_id, 0.0) + alpha_bought
            account.free_balance -= tao_amount
        elif transaction.action == 'unstake':
            alpha_amount = self._parse_amount(transaction.amount, account.alpha_stakes.get(transaction.subnet_id, 0.0))
            tao_bought = subnet.unstake(alpha_amount)
            account.alpha_stakes[transaction.subnet_id] = account.alpha_stakes.get(transaction.subnet_id, 0.0) - alpha_amount
            account.free_balance += tao_bought

    def _calculate_emission(self) -> Dict[int, float]:
        """
        Calculate emission distribution across non-root subnets.

        Formula:
            emission_share = subnet_tao_in / total_tao_in

        Returns:
            Dict[int, float]: Mapping of subnet IDs to their emission shares
        """
        emission = {s.id: s.tao_in for s in self.subnets.values() if not s.is_root}
        total = sum(emission.values())
        return {sid: e / total if total else 0.0 for sid, e in emission.items()}

    def _calculate_dividends(self, subnet_id: int) -> Dict[int, float]:
        """
        Calculate dividend distribution shares for accounts staked in a subnet.

        For each account, calculates a weighted combination of:
        1. Local weight (only for non-root subnets):
           - Calculate: (account_alpha_stake / subnet_alpha_out) * subnet_tao_in
           - Normalize: local_weight / sum(local_weights)

        2. Global weight (across all subnets):
           - For root subnet: account_alpha_stake * root_weight
           - For other subnets: (account_alpha_stake / subnet_alpha_out) * subnet_tao_in
           - Sum weights across all subnets
           - Normalize: global_weight_sum / sum(all_global_weights)

        Final dividend share formula:
            dividend = global_split * normalized_global_weight + 
                      (1 - global_split) * normalized_local_weight

        Args:
            subnet_id (int): ID of the subnet to calculate dividends for

        Returns:
            Dict[int, float]: Mapping of account IDs to their dividend shares,
                             where shares sum to 1.0
        """
        subnet = self.subnets.get(subnet_id)
        if not subnet:
            return {}

        weights = self._calculate_weights()
        local_weights = {
            acc_id: subnet.weight(account.alpha_stakes.get(subnet_id, 0.0))
            for acc_id, account in self.accounts.items()
            if subnet_id in account.alpha_stakes
        }

        total_local = sum(local_weights.values())
        total_global = sum(weights.values())

        return {
            acc_id: (
                self.global_split * (weights.get(acc_id, 0.0) / total_global if total_global else 0.0) +
                (1 - self.global_split) * (local_weights.get(acc_id, 0.0) / total_local if total_local else 0.0)
            )
            for acc_id in self.accounts
        }

    def _calculate_weights(self) -> Dict[int, float]:
        """
        Calculate global weights for all accounts across all subnets.

        Weight calculation per subnet stake:
            For root subnet:
                weight = alpha_stake * root_weight
            For non-root subnets:
                weight = (alpha_stake / subnet_alpha_out) * subnet_tao_in

        Total weight per account:
            account_weight = sum(stake_weights across all subnets)

        Returns:
            Dict[int, float]: Mapping of account IDs to their global weights
        """
        weights = defaultdict(float)
        for subnet in self.subnets.values():
            for acc_id, account in self.accounts.items():
                if subnet.id in account.alpha_stakes:
                    alpha = account.alpha_stakes[subnet.id]
                    weight = subnet.weight(alpha * self.root_weight if subnet.is_root else alpha)
                    weights[acc_id] += weight
        return dict(weights)

    def get_state(self, block: int) -> Dict[str, Any]:
        """Get complete state at given block"""
        emissions = self._calculate_emission()
        
        accounts_state = [
            account.get_state(self.subnets)
            for account in self.accounts.values()
        ]
        
        subnets_state = [
            subnet.get_state(
                emissions,
                self._calculate_dividends(subnet.id) if not subnet.is_root else {}
            )
            for subnet in self.subnets.values()
        ]
        
        network_state = {
            'tao_supply': self.tao_supply,
            'sum_prices': sum(s.alpha_price() 
                for s in self.subnets.values() 
                if not s.is_root)
        }
        
        return {
            'block': block,
            'accounts': accounts_state,
            'subnets': subnets_state,
            'network': network_state
        }
